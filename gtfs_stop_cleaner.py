#!/usr/bin/python2

from imposm.parser import OSMParser
from common import read_gtfs_stops
from collections import OrderedDict, defaultdict
import sys
from math import radians, cos, sin, asin, sqrt
import csv

# Stolen from http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
def haversine((lat1, lon1), (lat2, lon2)):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    # 6367 km is the radius of the Earth
    km = 6367 * c
    return km*1000.0


def read_osm_stops(osmfile):
	stop_coords = defaultdict(list)
	def handle_node(node):
		if (node[1].get('highway') != 'bus_stop' and
                    node[1].get('railway') != 'tram_stop'):
                    return
		if 'ref' not in node[1]: return
		ref = node[1]['ref']
		if not ref: return
		stop_coords[ref].append(node[2])

	def handle_nodes(nodes):
		for node in nodes:
			handle_node(node)
	OSMParser(nodes_callback=handle_nodes).parse(osmfile)
	return stop_coords

def fit_gtfs_stops(osmfile, stopsfile, distance_threshold=200.0):
	osmstops = read_osm_stops(osmfile)
	reader = read_gtfs_stops(open(stopsfile))
	names = reader.tupletype._fields
	writer = csv.writer(sys.stdout)
	writer.writerow(names)
	#import matplotlib.pyplot as plt
	position_errors = []
	for stop in reader:
		row = OrderedDict(zip(names, stop))
		candidates = []
		for candidate in osmstops[row['stop_code']]:
			lat, lon = candidate[::-1]
			distance = haversine((lat, lon), (float(row['stop_lat']), float(row['stop_lon'])))
			candidates.append((distance, (lat, lon)))

		if len(candidates) > 0:
			error, (lat, lon) = min(candidates)
			position_errors.append(error)
			if error < distance_threshold:
				row['stop_lat'] = lat
				row['stop_lon'] = lon
			else:
				print >>sys.stderr, "Huge error %f for stop %s"%(error, row['stop_code'])
		else:
			if row['stop_code']:
				print >>sys.stderr, "No OSM stop for %s"%(row['stop_code'])
		writer.writerow(row.values())
	sys.stdout.flush()
	#plt.hist(filter(lambda x: x < distance_threshold, position_errors), bins=50)
	#plt.show()


if __name__ == "__main__":
	import argh
	argh.dispatch_command(fit_gtfs_stops)
