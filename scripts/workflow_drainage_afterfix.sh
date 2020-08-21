fct-drainage flow outlets -j 6 -p
fct-drainage flow aggregate

fct-drainage drainage dispatch --exterior off
fct-drainage drainage accumulate -w -j 6 -p
fct-drainage drainage vectorize -j 6 -p -a 5.0
fct-drainage drainage aggregate

fct-drainage streams sources
fct-drainage streams vectorize -j 6 -p
fct-drainage streams aggregate
fct-drainage streams rasterize -j 6 -p

# fct-tiles buildvrt default acc
# fct-tiles buildvrt default drainage-raster-from-sources