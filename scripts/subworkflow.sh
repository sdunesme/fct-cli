#!/bin/bash

AXE=$1

# 1. Relative heights
# -------------------
fct-corridor shortest-height -j 32 $AXE
fct-corridor hand -j 32 $AXE

# 2. Delineate Flood-plain/Valley-bottom
# --------------------------------------
# also creates spatial reference system,
# with measure and distance from refrence axis

# -> create valley mask from HAND : HANDBuffer => ValleyMask
fct-corridor valleymask -j 32 $AXE
# -> create valley swaths, measure valleybottom
fct-swath discretize -j 32 $AXE
# TODO: manual swath corrections/edits
# TODO: update swath raster/valley mask from polygons
# fct-swath update -j 32 $AXE
# fct-swath simplify $AXE

# calculate drainage area before using medial axis
fct-metrics drainage-area -j 32 $AXE
## fct-plot drainage-area

# 2bis. Create better swaths from FP medial axis
# ----------------------------------------------

# optional step
# create better swath discretization
# from valley medial axis
fct-corridor medialaxis --simplify $AXE    
fct-swath discretize --medialaxis -j 32 $AXE
# TODO: manual swath corrections/edits
# TODO: update medialaxis swath raster from polygons
# fct-swath update --medialaxis -j 6
# fct-swath simplify --medialaxis

# 2ter. Backup & restart from beginning :)
# ----------------------------------------
fct-files backup $AXE
fct-files backup-hand -j 32 $AXE
fct-corridor prepare-from-backup $AXE

# même commande que fct-swath discretize mais paramétrée
# pour utiliser ax_nearest_heigth comme masque de fond de vallée
fct-swath create -j 32 $AXE
# fct-swath simplify # Uniquement possible si les swath ont été corrigés à la main

# 3. Elevation swath profiles & Improved FP Delineation
# -----------------------------------------------------
fct-swath profile elevation -j 32 $AXE
fct-swath export elevation $AXE
fct-metrics talweg $AXE
## fct-plot talweg-height 

# -> valley bottom mask, adjusted from talweg height/depth
# TODO déterminer seuil de hauteur par DGO f(largeur FDV, surface drainée)
fct-corridor refine-valley-mask -j 32 $AXE # delineate
fct-swath axes -j 32 $AXE

# 4. Height relative to FP
# ------------------------
# étape indépendante de refine-valley-mask
# (dépend de elevation-swath-profiles)
fct-corridor valley-profile $AXE # Possibles bug sur les swaths en erreur
## fct-plot profile-elevation --floodplain
fct-corridor height-above-valley-floor -j 32 $AXE

fct-corridor talweg-profile $AXE
## fct-plot profile-elevation --talweg

# 5. Landcover continuity Analysis
# --------------------------------
# fct-corridor landcover -j 6
# fct-corridor continuity -j 6
# fct-corridor continuity-weighted -j 6
# fct-corridor continuity-remap -j 6


# 6. Swath Profiles & Metrics Extraction
# --------------------------------------
fct-swath profile valleybottom -j 32 $AXE
fct-swath export valleybottom $AXE
# fct-metrics corridor-width
fct-metrics valleybottom-width $AXE

fct-swath profile landcover -lc landcover-hmvt -j 32 $AXE
fct-swath export landcover -lc landcover-hmvt $AXE
# fct-swath profile continuity $AXE
fct-metrics landcover-width -lc landcover-hmvt $AXE # Bug possible sur les swath en erreur
# fct-metrics continuity-width $AXE

fct-historical merge-landcover -ds metrics_width_landcover $AXE

fct-metrics planform $AXE