#!/usr/bin/python
import os
import sys
import time
import datetime
import json

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

def jore_shape_mapfit(map_file, projection, shape_json, whitelist=None, search_region=100.0, node_ids=False):

	if whitelist:
		whitelist = set(whitelist.split(','))

	with open(shape_json) as shape_file:
		shapes = json.load(shape_file).get("data").get("networkByDateAsGeojson")

	print "opened file"

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
	if whitelist:
		shapes = [s for s in shapes if s[0] in whitelist]

	start_time = time.time()
	results = (do_fit(s) for s in shapes)
	output = {'type': "FeatureCollection", 'features': []}
	extra_cols = []
	if node_ids:
		extra_cols.append('node_id')
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

		extra_cols = []
		if node_ids:
			ids = [p if p > 0 else "" for p in ids]
			extra_cols.append(ids)
		output['features'].append({'type': 'Feature', 'properties': shape_props, 'geometry': {'type': 'LineString', 'coordinates': [[lon, lat] for (lat, lon) in shape_coords]}})
	
	with open('out.json', 'w') as outfile:
		json.dump(output, outfile)

if __name__ == '__main__':
	import argh
	argh.dispatch_command(jore_shape_mapfit)

