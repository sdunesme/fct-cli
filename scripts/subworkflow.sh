#!/bin/bash

AXE=$1

fct-swath -c /local/sdunesme/BV_Isere/FCT/config.ini valleybottom -j 32 $AXE
fct-metrics -c /local/sdunesme/BV_Isere/FCT/config.ini valleybottom-width $AXE