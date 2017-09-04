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

cp $TMP_DIR/stops.fitted.txt $GTFS_DIR/stops.txt

zip -j $RESULT_FILE $GTFS_DIR/*

rm -r $TMP_DIR
