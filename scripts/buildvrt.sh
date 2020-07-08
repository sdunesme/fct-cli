# Global Datasets

find LANDCOVER -name "CESBIO_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 LANDCOVER_2018.vrt
find POPULATION -name "POP_INSEE_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 POP_2015.vrt
find ACC -name "POP_INSEE_ACC_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 POP_2015_ACC.vrt
find ACC -name "CESBIO_ACC_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 LANDCOVER_2018_ACC.vrt

# Per axis Datasets

find 10K -name "FLOW_DISTANCE_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 FLOW_DISTANCE.vrt
find 10K -name "FLOW_HEIGHT_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 FLOW_HEIGHT.vrt
find 10K -name "AXIS_MEASURE_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 AXIS_MEASURE.vrt
find 10K -name "AXIS_DISTANCE_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 AXIS_DISTANCE.vrt
find 10K -name "DGO_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 DGO.vrt
find 10K -name "NEAREST_HEIGHT_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 NEAREST_HEIGHT.vrt
find 10K -name "NEAREST_DISTANCE_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 NEAREST_DISTANCE.vrt
find 10K -name "VALLEY_BOTTOM_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 VALLEY_BOTTOM.vrt
find 10K -name "VALLEY_DISTANCE_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 VALLEY_DISTANCE.vrt

find 10K -name "LANDCOVER_CONTINUITY_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 LANDCOVER_CONTINUITY.vrt

find 10k -name "BUFFER30_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 BUFFER30.vrt
find 10k -name "BUFFER100_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 BUFFER100.vrt
find 10k -name "BUFFER200_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 BUFFER200.vrt
find 10k -name "BUFFER1000_*.tif" | xargs gdalbuildvrt -a_srs EPSG:2154 BUFFER1000.vrt
