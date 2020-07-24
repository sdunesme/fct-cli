#!/bin/bash

function mkvrt {
    SUBDIR=$1
    PREFIX=$2
    PATTERN="$PREFIX"_*.tif
    find $SUBDIR -name "$PATTERN" |
        xargs gdalbuildvrt -a_srs EPSG:2154 $PREFIX.vrt
}

function translate {
    VRT=$1
    gdal_translate -of gtiff -co TILED=YES -co COMPRESS=DEFLATE $VRT $(basename $VRT .vrt).tif
}

# Copies from regional processing

mkvrt 10K RGE5M
mkvrt 10K FLOW_RGE5M
mkvrt 10K ACC_RGE5M

# Global Datasets

mkvrt 10K LANDCOVER_2018 LANDCOVER_2018.vrt
mkvrt 10K POP_2015
mkvrt 10K SNV_2015
# find ACC -name "POP_INSEE_ACC_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 POP_2015_ACC.vrt
# find ACC -name "CESBIO_ACC_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 LANDCOVER_2018_ACC.vrt

# Per axis Datasets

mkvrt 10K FLOW_DISTANCE
mkvrt 10K FLOW_HEIGHT

mkvrt 10K NEAREST_HEIGHT
mkvrt 10K NEAREST_DISTANCE

mkvrt 10K AXIS_MEASURE
mkvrt 10K AXIS_DISTANCE
mkvrt 10K DGO

mkvrt 10K VALLEY_BOTTOM
mkvrt 10K VALLEY_DISTANCE

mkvrt 10K LANDCOVER_CLASSES
mkvrt 10K LANDCOVER_CONTINUITY

mkvrt 10k BUFFER_DISTANCE
mkvrt 10K BUFFER_MASK
mkvrt 10K BUFFER_PROFILE

mkvrt 10K SUBGRID_WATERSHED
