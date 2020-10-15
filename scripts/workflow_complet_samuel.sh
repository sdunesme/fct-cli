# Préparer le MNT avec une valeur de nodata correctement configurée
# Configurer correctement les chemins de fichiers dans config.ini
# Préparer la grille 10k avec fct/drainage/CreateTiles.py
# Préparer le référentiel hydro avec un champ AXIS
# Les sources ne doivent pas être multiparties
# Problèmes avec les tronçons frontaliers car pas de MNT en Suisse ! 

# export FCT_TILESET=10kbis

# Plan de drainage
fct-drainage prepare mktiles -j 8 -p --exterior off
fct-tiles buildvrt default dem
fct-drainage prepare smooth -j 8 -p --window 5
fct-tiles buildvrt default smoothed
fct-drainage prepare drape -ds smoothed

fct-drainage watershed labels -ds smoothed -b 2.0 -j 8 -p
fct-drainage watershed resolve
fct-drainage watershed dispatch -j 8 -p

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

# Préparation des axes
fct-corridor setup

# Préparer le fichier mapping.csv au préalable
fct-metrics data-landcover -lc landcover-hmvt -j 32
fct-tiles buildvrt default landcover-hmvt

## Remplacer $axe par le numéro d'axe
## Pour traiter les axes a la chaine : for axe in $(seq 1 298); do fct-corridor shortest-height -j 8 $axe; done
fct-corridor shortest-height -j 32 $axe
fct-corridor hand -j 32 $axe
fct-corridor valleymask -j 32 $axe
fct-swath discretize -j 32 $axe
fct-corridor medialaxis $axe
# fct-swath discretize -j 8 --medialaxis True $axe
fct-swath discretize --talweg True -j 32 $axe # Customisé par Samuel. A confirmer avec Christophe
# Refaire les DGO sur l'axe de référence

fct-swath elevation -j 32 $axe
fct-metrics planform $axe
fct-metrics talweg $axe
#fct-corridor valley-profile $axe # Bug sur les swaths en erreur
fct-corridor refine-valley-mask -j 32 $axe

fct-swath landcover -lc landcover-hmvt -j 32 207
# Il faut supprimer les swath en erreur

fct-metrics valleybottom-width 207
fct-plot landcover-profile-lr 207

# Liste axes Isere 
165,969,970,968,422,766,546,155,761,156,415,631,755,149,632,150,891,412,535,536,751,531,31,269,143,888,529,750,403,265,745,881,140,620,400,397,616,805,873,677,676,800,578,451,797,12,573,9,450,186,929,791,567,180,661,304,784,562,435,297,782,295,431,229,230,101,776,835,836,907,483,355,356,904,215,92,478,701,90,352,702,699,962,958,467,689,76,461,462,945,683,682,455,742,132,939,516,735,252,249,123,385,869,509,868,5,725,726,239,502,720,372,107,231,370,232,106,103,365,366,974,363,773,294