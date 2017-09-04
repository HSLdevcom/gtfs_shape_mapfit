#!/bin/bash
set -e

MAP_FILE=$1
PROJECTION=$2
GTFS_FILE=$3
RESULT_FILE=$4
TOOL_DIR="$(dirname "$0")"

if [ $# -lt 4 ]
then
	echo "Usage: $0 map_file projection original_gtfs_file new_gtfs_file"
	exit 1
fi

TMP_DIR=`mktemp -d -t fit_gtfs.XXXXX`
GTFS_DIR=$TMP_DIR/orig_gtfs
mkdir $GTFS_DIR
unzip $GTFS_FILE -d $TMP_DIR/orig_gtfs

"$TOOL_DIR"/gtfs_stop_cleaner.py $MAP_FILE $GTFS_DIR/stops.txt 2>&1 >$TMP_DIR/stops.fitted.txt |tee $TMP_DIR/stops.log.txt >&2
"$TOOL_DIR"/gtfs_shape_mapfit2.py $MAP_FILE $PROJECTION $GTFS_DIR \
	2>&1 >$TMP_DIR/shapes.fitted.txt |tee $TMP_DIR/shapefit_stats.txt >&2
"$TOOL_DIR"/filter_bad_fits.py $TMP_DIR/shapefit_stats.txt $TMP_DIR/shapes.fitted.txt $GTFS_DIR/shapes.txt \
	2>&1 >$TMP_DIR/shapes.filtered.txt |tee $TMP_DIR/shapefit.log.txt >&2
"$TOOL_DIR"/generate_geojson.py $TMP_DIR/stops.log.txt $TMP_DIR/shapefit.log.txt $GTFS_DIR/shapes.txt $TMP_DIR/shapes.fitted.txt > $TMP_DIR/geojson.txt


cp $TMP_DIR/shapes.filtered.txt $GTFS_DIR/shapes.txt
cp $TMP_DIR/stops.fitted.txt $GTFS_DIR/stops.txt
cp $TMP_DIR/geojson.txt $GTFS_DIR/match.geojson

zip -j $RESULT_FILE $GTFS_DIR/*

rm -r $TMP_DIR
