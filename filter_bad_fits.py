#!/usr/bin/python2

import itertools, sys, math

from common import read_gtfs_shapes, GtfsShapeWriter

def float_or_none(val):
	if val == 'None':
		return None
	return float(val)

def percentile(x, perc):
	x = sorted(x)
	n = len(x)
	if n == 0:
		return None
	
	# Should handle ties, but probably
	# doesn't matter here
	return x[int((n-1)*perc)]
		

def filter_bad_fits(statsfile, fitted_shapes, orig_shapes, criteria_quantiles=2.0):
	stats = []
	for row in open(statsfile):
		row = row.split(';')
		row[1] = float_or_none(row[1])
		row[2] = float_or_none(row[2])
		stats.append(row)
	
	fitted = dict(read_gtfs_shapes(open(fitted_shapes)))
	orig = dict(read_gtfs_shapes(open(orig_shapes)))
	writer = GtfsShapeWriter(sys.stdout)
	stats.sort(key=lambda r: r[3])
	for transit_type, rows in itertools.groupby(stats, lambda r: r[3]):
		rows = list(rows)
		cols = zip(*rows)
		likelihoods = cols[1]
		outliers = cols[2]
		scores = [-l for l, o in zip(likelihoods, outliers)
			if l is not None and o == 0]
		try:
			minscore = min(scores)
			scores = [math.sqrt(s-minscore) for s in scores]
			score_limit = percentile(scores, 0.75)*criteria_quantiles
		except ValueError:
			score_limit = None
		
		print >>sys.stderr, "Score limit %s for %s"%(score_limit, transit_type)
		for row in rows:
			shape_id = row[0]
			if score_limit is None:
				writer(shape_id, fitted[shape_id])
				continue
			if row[2] > 0:
				print >>sys.stderr, "Outliers found, using original;Route ID: %s;Outliers: %i;"%(row[0], row[2])

			lik = row[1]
			score = math.sqrt(-lik - minscore)
			if score > score_limit:
				print >>sys.stderr, "Probably bad fit, using original;Route ID: %s;Score: %f;Score limit: %f;"%(row[0], score, score_limit)
				writer(shape_id, orig[shape_id])

			else:
				#print >>sys.stderr, "Good fit %s"%row[0]
				writer(shape_id, fitted[shape_id])


if __name__ == '__main__':
	import argh
	argh.dispatch_command(filter_bad_fits)
