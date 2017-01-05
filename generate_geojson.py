#!/usr/bin/python2
# -*- coding: utf-8 -*-

import sys, ast
reload(sys)
sys.setdefaultencoding('utf8')

def generate_geojson(stop_file, shapefit_file, shape_file_original, shape_file_fitted):
	stop_features = []
	shape_features = []
	for row in open(stop_file):
		row = row.split(';')
		error_type = row[0]
		if (error_type.startswith("Huge error") or error_type.startswith("No OSM stop")):
			stop_id = row[1].split(':')[1].lstrip()
			coordinates_jore = ast.literal_eval(row[2])
			feature_jore = '{"type": "Feature", "geometry": {"type": "Point","coordinates": %s}, "properties": {"stop_id": "%s", "error_type": "%s", "source": "JORE" }}'%(coordinates_jore, stop_id, error_type)
			stop_features.append(feature_jore)
			if (error_type.startswith("Huge error")):
				coordinates_osm = ast.literal_eval(row[3])
				feature_osm = '{"type": "Feature", "geometry": {"type": "Point","coordinates": %s},"properties": {"stop_id": "%s", "error_type": "%s", "source": "OSM" }}'%(coordinates_osm, stop_id, error_type)
				stop_features.append(feature_osm)
	
	for row in open(shapefit_file):
		row = row.split(';')
		error_type = row[0]
		if (error_type.startswith("Probably bad fit") or error_type.startswith("Outliers found")):
			route_id = row[1].split(':')[1].lstrip()
			coordinates_jore = find_coordinates(shape_file_original, route_id)
			coordinates_osm = find_coordinates(shape_file_fitted, route_id)
			if (error_type.startswith("Probably bad fit")):
				score = row[2].split(':')[1].lstrip()
				score_limit = row[3].split(': ')[1].lstrip()
				properties_jore = '{"route_id": "%s", "error_type": "%s", "source": "JORE", "score" : "%s", "limit" : "%s"}'%(route_id, error_type, score, score_limit)
				properties_osm = '{"route_id": "%s", "error_type": "%s", "source": "OSM", "score" : "%s", "limit" : "%s"}'%(route_id, error_type, score, score_limit)
			else:
				outliers = row[2].split(':')[1]
				properties_jore = '{"route_id": "%s", "error_type": "%s", "source": "JORE", "outliers" : "%s"}'%(route_id, error_type, outliers)
				properties_osm = '{"route_id": "%s", "error_type": "%s", "source": "OSM", "outliers" : "%s"}'%(route_id, error_type, outliers)
			feature_jore = '{"type": "Feature", "geometry": {"type": "LineString", "coordinates": %s}, "properties": %s}'%(coordinates_jore, properties_jore)
			feature_osm = '{"type": "Feature", "geometry": {"type": "LineString", "coordinates": %s}, "properties": %s}'%(coordinates_osm, properties_osm)
			shape_features.append(feature_jore)
			shape_features.append(feature_osm)
	all_features = stop_features + shape_features
	feature_collection = '{"type": "feature_collection", "features": [%s]}'%(", ".join([feature.decode('utf8') for feature in all_features]))
	print >>sys.stderr, "%s"%(feature_collection)

def find_coordinates(file, route_id):
	coordinates = []
	for row in open(file):
		row = row.split(',')
		list_route_id = row[0]
		if route_id == list_route_id:
			coordinate_lat = ast.literal_eval(row[1])
			coordinate_lon = ast.literal_eval(row[2])
			coordinates.append([coordinate_lon, coordinate_lat])
	return coordinates

if __name__ == '__main__':
	import argh
	argh.dispatch_command(generate_geojson)