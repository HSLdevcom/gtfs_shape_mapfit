#!/usr/bin/python2
# -*- coding: utf-8 -*-

import sys, ast
reload(sys)
sys.setdefaultencoding('utf8')

def generate_geojson(stop_file, shapefit_file, shape_file_original, shape_file_fitted):
	stopFeatures = []
	shapeFeatures = []
	for row in open(stop_file):
		row = row.split(';')
		errorType = row[0]
		if (errorType.startswith("Huge error") or errorType.startswith("No OSM stop")):
			stopId = row[1].split(':')[1].lstrip()
			coordinatesJore = ast.literal_eval(row[2])
			featureJore = '{"type": "Feature", "geometry": {"type": "Point","coordinates": %s}, "properties": {"stopId": "%s", "errorType": "%s", "source": "JORE" }}'%(coordinatesJore, stopId, errorType)
			stopFeatures.append(featureJore)
			if (errorType.startswith("Huge error")):
				coordinatesOsm = ast.literal_eval(row[3])
				featureOsm = '{"type": "Feature", "geometry": {"type": "Point","coordinates": %s},"properties": {"stopId": "%s", "errorType": "%s", "source": "OSM" }}'%(coordinatesOsm, stopId, errorType)
				stopFeatures.append(featureOsm)
	
	for row in open(shapefit_file):
		row = row.split(';')
		errorType = row[0]
		if (errorType.startswith("Probably bad fit") or errorType.startswith("Outliers found")):
			routeId = row[1].split(':')[1].lstrip()
			coordinatesJore = find_coordinates(shape_file_original, routeId)
			coordinatesOsm = find_coordinates(shape_file_fitted, routeId)
			if (errorType.startswith("Probably bad fit")):
				score = row[2].split(':')[1].lstrip()
				scoreLimit = row[3].split(': ')[1].lstrip()
				propertiesJore = '{"routeId": "%s", "errorType": "%s", "source": "JORE", "score" : "%s", "limit" : "%s"}'%(routeId, errorType, score, scoreLimit)
				propertiesOsm = '{"routeId": "%s", "errorType": "%s", "source": "OSM", "score" : "%s", "limit" : "%s"}'%(routeId, errorType, score, scoreLimit)
			else:
				outliers = row[2].split(':')[1]
				propertiesJore = '{"routeId": "%s", "errorType": "%s", "source": "JORE", "outliers" : "%s"}'%(routeId, errorType, outliers)
				propertiesOsm = '{"routeId": "%s", "errorType": "%s", "source": "OSM", "outliers" : "%s"}'%(routeId, errorType, outliers)
			featureJore = '{"type": "Feature", "geometry": {"type": "LineString", "coordinates": %s}, "properties": %s}'%(coordinatesJore, propertiesJore)
			featureOsm = '{"type": "Feature", "geometry": {"type": "LineString", "coordinates": %s}, "properties": %s}'%(coordinatesOsm, propertiesOsm)
			shapeFeatures.append(featureJore)
			shapeFeatures.append(featureOsm)
	allFeatures = stopFeatures + shapeFeatures
	featureCollection = '{"type": "FeatureCollection", "features": [%s]}'%(", ".join([feature.decode('utf8') for feature in allFeatures]))
	print >>sys.stderr, "%s"%(featureCollection)

def find_coordinates(file, routeId):
	coordinates = []
	for row in open(file):
		row = row.split(',')
		listRouteId = row[0]
		if routeId == listRouteId:
			coordinateLat = ast.literal_eval(row[1])
			coordinateLon = ast.literal_eval(row[2])
			coordinates.append([coordinateLon, coordinateLat])
	return coordinates

if __name__ == '__main__':
	import argh
	argh.dispatch_command(generate_geojson)