# Préparer le MNT avec une valeur de nodata correctement configurée
# Configurer correctement les chemins de fichiers dans config.ini
# Créer un fichier .env là ou on lance les commandes : export FCT_CONFIG=/path/to/config.ini
# Préparer la grille 10k avec fct/drainage/CreateTiles.py
# Préparer le référentiel hydro avec un champ AXIS
# Les sources ne doivent pas être multiparties
# Problèmes avec les tronçons frontaliers car pas de MNT en Suisse ! 

# export FCT_TILESET=10kbis


# 0. Drainage plan
# ----------------
fct-drainage prepare mktiles -j 8 -p --exterior off
fct-tiles buildvrt default dem
fct-drainage prepare smooth -j 8 -p --window 5
fct-tiles buildvrt default smoothed
fct-drainage prepare drape -ds smoothed

# fct-drainage watershed labels -ds smoothed -b 2.0 -j 8 -p
# fct-drainage watershed resolve
# fct-drainage watershed dispatch -j 8 -p
fct-drainage watershed labels -j 8
fct-drainage watershed resolve
fct-drainage watershed dispatch -j 8

fct-drainage flat labels -j 8 -p
fct-drainage flat resolve
fct-drainage flat dispatch -j 8 -p
fct-tiles buildvrt default dem-drainage-resolved
fct-drainage flat depthmap -j 8 -p
fct-tiles buildvrt default depression-depth

fct-drainage flow calculate -j 8 -p --exterior off
fct-tiles buildvrt default flow
fct-drainage flow outlets -j 8 -p
fct-drainage flow aggregate

fct-drainage drainage dispatch --exterior off
fct-drainage drainage accumulate -j 8 -p
fct-tiles buildvrt default acc
fct-drainage drainage vectorize -j 8 -p -a 5.0
fct-drainage drainage aggregate

fct-drainage streams from-sources
fct-drainage streams vectorize -j 8 -p
fct-drainage streams aggregate
fct-drainage streams rasterize -j 8 -p
fct-tiles buildvrt default drainage-raster-from-sources
fct-drainage streams noflow -j 8 -p
fct-drainage streams aggregate-noflow
# Reste à fixer les noflows. On continue sans le RHTS et en utilisant le REF HYDRO

# 0bis. Data preparation
# ----------------------
# Préparer le fichier mapping.csv au préalable
fct-metrics data-landcover -lc landcover-hmvt -j 8
fct-tiles buildvrt default landcover-hmvt

# Préparation des axes
fct-corridor setup

## Dans la suite, remplacer $AXE par le numéro d'axe
## Pour traiter les axes a la chaine, placer les commandes dans subworkflow.sh puis lancer parallelize_subworkflow.sh
## Ou : for path in AXES/AX*; do export AXE=${path:(-4)}; fct-blablaba $AXE; done

# 1. Relative heights
# -------------------
fct-corridor shortest-height -j 8 $AXE
fct-corridor hand -j 8 $AXE

# 2. Delineate Flood-plain/Valley-bottom
# --------------------------------------
# also creates spatial reference system,
# with measure and distance from refrence axis

# -> create valley mask from HAND : HANDBuffer => ValleyMask
fct-corridor valleymask -j 8 $AXE
# -> create valley swaths, measure valleybottom
fct-swath discretize -j 8 $AXE
# TODO: manual swath corrections/edits
# TODO: update swath raster/valley mask from polygons
# fct-swath update -j 8 $AXE
# fct-swath simplify $AXE

# calculate drainage area before using medial axis
fct-metrics drainage-area -j 8 $AXE
## fct-plot drainage-area

# 2bis. Create better swaths from FP medial axis
# ----------------------------------------------

# optional step
# create better swath discretization
# from valley medial axis
fct-corridor medialaxis --simplify $AXE    
fct-swath discretize --medialaxis -j 8 $AXE
# TODO: manual swath corrections/edits
# TODO: update medialaxis swath raster from polygons
# fct-swath update --medialaxis -j 6
# fct-swath simplify --medialaxis

# 2ter. Backup & restart from beginning :)
# ----------------------------------------
fct-files backup $AXE
fct-files backup-hand -j 8 $AXE
fct-corridor prepare-from-backup $AXE

# même commande que fct-swath discretize mais paramétrée
# pour utiliser ax_nearest_heigth comme masque de fond de vallée
fct-swath create -j 8 $AXE
# fct-swath simplify # Uniquement possible si les swath ont été corrigés à la main

# 3. Elevation swath profiles & Improved FP Delineation
# -----------------------------------------------------
fct-swath profile elevation -j 8 $AXE
fct-swath export elevation $AXE
fct-metrics talweg $AXE
## fct-plot talweg-height 

# -> valley bottom mask, adjusted from talweg height/depth
# TODO déterminer seuil de hauteur par DGO f(largeur FDV, surface drainée)
fct-corridor refine-valley-mask -j 8 $AXE # delineate
fct-swath axes -j 8 $AXE

# 4. Height relative to FP
# ------------------------
# étape indépendante de refine-valley-mask
# (dépend de elevation-swath-profiles)
fct-corridor valley-profile $AXE # Possibles bug sur les swaths en erreur
## fct-plot profile-elevation --floodplain
fct-corridor height-above-valley-floor -j 8 $AXE

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
fct-swath profile valleybottom -j 8 $AXE
fct-swath export valleybottom $AXE
# fct-metrics corridor-width
fct-metrics valleybottom-width $AXE

fct-swath profile landcover -lc landcover-hmvt -j 8 $AXE
fct-swath export landcover -lc landcover-hmvt $AXE
# fct-swath profile continuity $AXE
fct-metrics landcover-width -lc landcover-hmvt $AXE # Bug possible sur les swath en erreur
# fct-metrics continuity-width $AXE

fct-historical merge-landcover -ds metrics_width_landcover $AXE
fct-historical clean-nodata -lc landcover-hmvt -ds metrics_width_multilandcover $AXE

fct-metrics planform $AXE

# fct-plot landcover-profile --variant HMVT_1934
# fct-plot landcover-profile-lr --variant HMVT_1934
# fct-plot continuity-profile
# fct-plot continuity-profile-lr

# fct-plot planform
# fct-plot amplitude

# 7. Hypsometry
# -------------------------
# fct-metrics hypsometry -j 8 $AXE

# fct-plot hypsometry

# Liste axes Isere 
# 165,969,970,968,422,766,546,155,761,156,415,631,755,149,632,150,891,412,535,536,751,531,31,269,143,888,529,750,403,265,745,881,140,620,400,397,616,805,873,677,676,800,578,451,797,12,573,9,450,186,929,791,567,180,661,304,784,562,435,297,782,295,431,229,230,101,776,835,836,907,483,355,356,904,215,92,478,701,90,352,702,699,962,958,467,689,76,461,462,945,683,682,455,742,132,939,516,735,252,249,123,385,869,509,868,5,725,726,239,502,720,372,107,231,370,232,106,103,365,366,974,363,773,294