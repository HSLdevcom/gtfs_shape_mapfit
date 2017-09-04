#!/usr/bin/python
import os
import sys
import time
import datetime
import json
import urllib2
import contextlib
import psycopg2

import pymapmatch.osmmapmatch as omm
from collections import defaultdict
import itertools

class ShapeError(Exception): pass

ROUTE_TYPE_FILTERS = {
	'TRAM': "TRAM_FILTER",
	'BUS': "BUSWAY_FILTER",
}

from threading import Lock, RLock, Thread
from Queue import Queue
stderr_lock = Lock()
def stderr(*args):
	with stderr_lock:
		print >>sys.stderr, ' '.join(args)

def jore_shape_mapfit(
		map_file,
		projection,
		connection_string
		graphql_endpoint="http://kartat.hsl.fi/jore/graphql",
		search_region=100.0
	):

	req = urllib2.Request(
		graphql_endpoint,
		'{"query":"query networkQuery { pointNetworkAsGeojson }","variables":null,"operationName":"networkQuery"}',
		{"Content-Type": "application/json", "Accept": "application/json"}
	)

	#urllib2.install_opener(urllib2.build_opener(urllib2.HTTPHandler(debuglevel=1)))

	with contextlib.closing(urllib2.urlopen(req)) as shape_stream:
		shapes = json.load(shape_stream).get("data").get("pointNetworkAsGeojson")

	print "opened file"

	conn = psycopg2.connect(connection_string)
	cur = conn.cursor()
	cur.execute("""CREATE TABLE jore.geometry (
		route_id   character varying(6) NOT NULL
		direction  character varying(1) NOT NULL
		date_begin date NOT NULL
		date_end   date NOT NULL
		mode       jore.mode
		geometry   geometry(LineString,4326)
		outliers   integer
		min_likelihood real
		)""")

	projection = omm.CoordinateProjector(projection)

	def sync(method):
		def synced(self, *args, **kwargs):
			with self.lock:
				stuff = method(self, *args, **kwargs)
			return stuff
		return synced

	class Graphs(defaultdict):
		def __init__(self):
			self.lock = RLock()

		__getitem__ = sync(defaultdict.__getitem__)
		__setitem__ = sync(defaultdict.__setitem__)
		__contains__ = sync(defaultdict.__contains__)

		def __missing__(self, type_filter):
			if type_filter is None:
				# print >>sys.stderr, "No map filter for route type %s"%type_filter
				self[type_filter] = None
				return None
			filt = getattr(omm, type_filter)
			# stderr("Loading graph for %s"%type_filter)
			graph = omm.OsmGraph(map_file, projection, filt)
                        # stderr("Loaded graph for %s"%type_filter)
			self[type_filter] = graph
			return graph
	graphs = Graphs()

	from multiprocessing.pool import ThreadPool
	def do_fit(shape):
		shape_coords = [(lat, lon) for [lon, lat] in shape["geometry"]["coordinates"]]
		route_type = shape["properties"]["mode"]
		type_filter = ROUTE_TYPE_FILTERS.get(route_type)
		graph = graphs[type_filter]

		if graph is None:
			return shape["properties"], shape_coords, [], [], None, None

		state_model = omm.DrawnGaussianStateModel(30, 0.05, graph)
		matcher = omm.MapMatcher2d(graph, state_model, search_region)

		coords = [projection(*c) for c in shape_coords]
		points = [omm.Point2d(*c) for c in coords]
		times = [0.0]*len(points)
		matcher.measurements(times, points)
		#for c in coords:
		#	matcher.measurement(0, *c)
		fitted_coords = [(p.x, p.y) for p in matcher.best_match_coordinates()]
		fitted_nodes = [p for p in matcher.best_match_node_ids()]
		fitted = [projection.inverse(*c) for c in fitted_coords]

		states = []
		state = matcher.best_current_hypothesis()
		while state:
			states.append(state)
			state = state.parent

		return shape["properties"], fitted, fitted_nodes, states, matcher, type_filter

	shapes = list(shapes["features"])

	start_time = time.time()
	results = (do_fit(s) for s in shapes)
	for i, (shape_props, shape_coords, ids, states, matcher, type_filter) in enumerate(results):
		shape_id = shape_props['route_id']
		likelihoods = [s.measurement_likelihood+s.transition_likelihood for s in states]
		time_spent = time.time() - start_time
		mean_time = time_spent/float(i+1)
		time_left = mean_time*(len(shapes)-i)
		status = "Shape %i/%i, approx %s left"%(i+1, len(shapes), datetime.timedelta(seconds=time_left))
		if len(likelihoods) == 0:
			minlik = None
			n_outliers = 0
		else:
			minlik = min(likelihoods)
			n_outliers = matcher.n_outliers
		logrow = shape_id, minlik, n_outliers, type_filter, status
		stderr(';'.join(map(str, logrow)))

		cur.execute(
			"INSERT INTO jore.geometry(%s, %s, %s, %s, %s::jore.mode, ST_GEOMETRYFROMTEXT(%s, 4326), %s, %s)",
			(
				shape_props['route_id'],
				shape_props['direction']
				shape_props['date_begin']
				shape_props['date_end']
				shape_props['mode']
				"LINESTRING(" + ",".join([str(lon) + " " + str(lat) for (lat, lon) in shape_coords]) + ")",
				n_outliers
				minlik
			)
		)

	conn.commit()
	cur.close()
	conn.close()

if __name__ == '__main__':
	import argh
	argh.dispatch_command(jore_shape_mapfit)
