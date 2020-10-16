#!/bin/bash

AXE=$1

fct-swath -c /local/sdunesme/BV_Isere/FCT/config.ini landcover -lc landcover-hmvt -j 32 $AXE
fct-swath -c /local/sdunesme/BV_Isere/FCT/config.ini export-landcover -lc landcover-hmvt $AXE
fct-historical -c /local/sdunesme/BV_Isere/FCT/config.ini merge-landcover $AXE