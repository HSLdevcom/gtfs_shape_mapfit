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
		if (errorType == "Huge error" or errorType == "No OSM stop"):
			coordinatesJore = ast.literal_eval(row[2])
			featureJore = '{"type": "Feature", "geometry": {"type": "Point","coordinates": %s}, "properties": {"stopId": "%s", "errorType": "%s", "source": "JORE" }}'%(coordinatesJore, row[1], errorType)
			stopFeatures.append(featureJore)
			if (errorType == "Huge error"):
				coordinatesOsm = ast.literal_eval(row[3])
				featureOsm = '{"type": "Feature", "geometry": {"type": "Point","coordinates": %s},"properties": {"stopId": "%s", "errorType": "%s", "source": "OSM" }}'%(coordinatesOsm, row[1], errorType)
				stopFeatures.append(featureOsm)
	
	for row in open(shapefit_file):
		row = row.split(';')
		errorType = row[0]
		if (errorType == "Probably bad fit" or errorType == "Outliers exist"):
			coordinatesJore = find_coordinates(shape_file_original, row[1])
			coordinatesOsm = find_coordinates(shape_file_fitted, row[1])
			if (errorType == "Probably bad fit"):
				propertiesJore = '{"lineId": "%s", "errorType": "%s", "source": "JORE", "score" : "%s", "limit" : "%s"}'%(row[1], errorType, row[2], row[3])
				propertiesOsm = '{"lineId": "%s", "errorType": "%s", "source": "OSM", "score" : "%s", "limit" : "%s"}'%(row[1], errorType, row[2], row[3])
			else:
				propertiesJore = '{"lineId": "%s", "errorType": "%s", "source": "JORE", "outliers" : "%s"}'%(row[1], errorType, row[2])
				propertiesOsm = '{"lineId": "%s", "errorType": "%s", "source": "OSM", "outliers" : "%s"}'%(row[1], errorType, row[2])
			featureJore = '{"type": "Feature", "geometry": {"type": "LineString", "coordinates": %s}, "properties": %s}'%(coordinatesJore, propertiesJore)
			featureOsm = '{"type": "Feature", "geometry": {"type": "LineString", "coordinates": %s}, "properties": %s}'%(coordinatesOsm, propertiesOsm)
			shapeFeatures.append(featureJore)
			shapeFeatures.append(featureOsm)
	allFeatures = stopFeatures + shapeFeatures
	featureCollection = '{"type": "FeatureCollection", "features": [%s]}'%(", ".join([feature.decode('utf8') for feature in allFeatures]))
	print >>sys.stderr, "%s"%(featureCollection)

def find_coordinates(file, stopId):
	coordinates = []
	for row in open(file):
		row = row.split(',')
		listStopId = row[0]
		if stopId == listStopId:
			coordinateLat = ast.literal_eval(row[1])
			coordinateLon = ast.literal_eval(row[2])
			coordinates.append([coordinateLon, coordinateLat])
	return coordinates

if __name__ == '__main__':
	import argh
	argh.dispatch_command(generate_geojson)