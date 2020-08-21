# export FCT_TILESET=10kbis

fct-drainage prepare mktiles -j 6 -p --exterior off
fct-tiles buildvrt default dem
fct-drainage prepare smooth -j 6 -p --window 5
fct-tiles buildvrt default smoothed
fct-drainage prepare drape -ds smoothed

fct-drainage watershed labels -ds smoothed -b 2.0 -j 6 -p
fct-drainage watershed resolve
fct-drainage watershed dispatch -j 6 -p

fct-drainage flat labels -j 6 -p
fct-drainage flat resolve
fct-drainage flat dispatch -j 6 -p
fct-tiles buildvrt default dem-drainage-resolved
fct-drainage flat depthmap -j 6 -p
fct-tiles buildvrt default depression-depth

fct-drainage flow calculate -j 6 -p --exterior off
fct-tiles buildvrt default flow
fct-drainage flow outlets -j 6 -p
fct-drainage flow aggregate

fct-drainage drainage dispatch --exterior off
fct-drainage drainage accumulate -j 6 -p
fct-tiles buildvrt default acc
fct-drainage drainage vectorize -j 6 -p -a 5.0
fct-drainage drainage aggregate

fct-drainage streams sources
fct-drainage streams vectorize -j 6 -p
fct-drainage streams aggregate
fct-drainage streams rasterize -j 6 -p
fct-tiles buildvrt default drainage-raster-from-sources
fct-drainage streams noflow -j 6 -p
fct-drainage streams aggregate-noflow
