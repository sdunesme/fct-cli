# Préparer le MNT avec une valeur de nodata correctement configurée
# Configurer correctement les chemins de fichiers dans config.ini
# Préparer la grille 10k avec fct/drainage/CreateTiles.py
# Préparer le référentiel hydro avec un champ AXIS
# Les sources ne doivent pas être multiparties
# Problèmes avec les tronçons frontaliers car pas de MNT en Suisse ! 

# export FCT_TILESET=10kbis

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

fct-corridor setup

# Remplacer 207 par le numéro d'axe
fct-corridor shortest-height -j 8 207
fct-corridor hand -j 8 207
fct-corridor valleymask -j 8 207
fct-swath discretize -j 8 207
fct-corridor medialaxis 207
# fct-swath discretize -j 8 --medialaxis True 207
fct-swath discretize --talweg True -j 8 207 # Customisé par Samuel. A confirmer avec Christophe

fct-swath elevation -j 8 207
fct-metrics planform 207
fct-metrics talweg 207
fct-corridor valley-profile 207
fct-corridor refine-valley-mask -j 8 207

# Préparer le fichier mapping.csv au préalable
fct-metrics data-landcover -lc landcover-hmvt -j 8
fct-tiles buildvrt default landcover-hmvt
fct-swath landcover --lc landcover-hmvt -j 8 207
# Il faut supprimer les swath en erreur

fct-metrics valleybottom-width 207
fct-plot landcover-profile-lr 207