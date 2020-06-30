# coding: utf-8

"""
Sequence :

4. Accumulate/Resolve Acc Graph/InletAreas
5. FlowAccumulation (*)
6. StreamToFeature (*)

(*) Possibly Parallel Steps

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from collections import defaultdict, Counter
import itertools
from operator import itemgetter

import numpy as np
import click

import fiona
import fiona.crs
import rasterio as rio

import speedup
import terrain_analysis as ta

from config import tileindex, filename

def CreateSourcesGraph():
    """
    DOCME
    """

    tile_index = tileindex()
    DEM = filename('dem', 'input')
    sources = filename('sources', 'input')

    click.secho('Build sources graph', fg='cyan')

    graph = dict()
    indegree = Counter()

    dem = rio.open(DEM)

    with click.progressbar(tile_index) as progress:
        for row, col in progress:

            tile = tile_index[(row, col)].gid
            inlet_shapefile = filename('inlets', row=row, col=col)
            flow_raster = filename('flow', row=row, col=col)

            with rio.open(flow_raster) as ds:

                flow = ds.read(1)
                height, width = flow.shape

                with fiona.open(inlet_shapefile) as fs:
                    for feature in fs:

                        # connect outlet->inlet

                        from_tile = feature['properties']['FROM']
                        area = 0.0
                        from_i, from_j = dem.index(feature['properties']['FROMX'], feature['properties']['FROMY'])
                        i, j = dem.index(*feature['geometry']['coordinates'])
                        graph[(from_tile, from_i, from_j)] = (tile, i, j, area)
                        indegree[(tile, i, j)] += 1

                        # connect inlet->tile outlet

                        loci, locj = ds.index(*feature['geometry']['coordinates'])
                        locti, loctj = ta.outlet(flow, loci, locj)
                        ti, tj = dem.index(*ds.xy(locti, loctj))

                        if (locti, loctj) == (loci, locj):
                            continue
                        
                        if ti >= 0 and tj >= 0:
                            graph[(tile, i, j)] = (tile, ti, tj, 0)
                            indegree[(tile, ti, tj)] += 1

                with fiona.open(sources) as fs:
                    for feature in fs:

                        loci, locj = ds.index(*feature['geometry']['coordinates'])

                        if not all([loci >= 0, loci < height, locj >= 0, locj < width]):
                            continue

                        # connect exterior->inlet

                        i, j = dem.index(*feature['geometry']['coordinates'])
                        area = 1.0
                        graph[(-2, i-1, j-1)] = (tile, i, j, area)
                        indegree[(tile, i, j)] += 1

                        # connect inlet->tile outlet

                        locti, loctj = ta.outlet(flow, loci, locj)
                        ti, tj = dem.index(*ds.xy(locti, loctj))

                        if (locti, loctj) == (loci, locj):
                            continue
                        
                        if ti >= 0 and tj >= 0:
                            graph[(tile, i, j)] = (tile, ti, tj, 0)
                            indegree[(tile, ti, tj)] += 1


    dem.close()

    click.secho('Created graph with %d nodes' % len(graph), fg='green')

    return graph, indegree

def TileInletSources(tile, keys, areas):
    """
    Output inlet points,
    attributed with the total upstream drained area.
    """

    row = tile.row
    col = tile.col
    gid = tile.gid

    crs = fiona.crs.from_epsg(2154)
    driver = 'ESRI Shapefile'
    schema = {
        'geometry': 'Point',
        'properties': [
            ('TILE', 'int')
        ]
    }
    options = dict(driver=driver, crs=crs, schema=schema)

    dem_file = filename('dem', 'input')
    dem = rio.open(dem_file)

    cum_areas = defaultdict(lambda: 0.0)

    for key in keys:
        cum_areas[key[1:]] += areas.get(key[1:], 0)

    with fiona.open(filename('inlet-sources', row=row, col=col), 'w', **options) as dst:
        for i, j in cum_areas:

            x, y = dem.xy(i, j)
            area = cum_areas[i, j]
            if area > 0.0:
                geom = {'type': 'Point', 'coordinates': [x, y]}
                props = {'TILE': gid}
                feature = {'geometry': geom, 'properties': props}
                dst.write(feature)

    dem.close()


def InletSources():
    """
    Accumulate areas across tiles
    and output per tile inlet shapefiles
    with contributing area flowing into tile.
    """

    tile_index = tileindex()
    tiles = {tile.gid: tile for tile in tile_index.values()}

    graph, indegree = CreateSourcesGraph()

    click.secho('Accumulate areas', fg='cyan')
    areas, res = speedup.graph_acc(graph)

    keys = sorted(graph.keys() | indegree.keys(), key=itemgetter(0))
    groups = itertools.groupby(keys, key=itemgetter(0))

    click.secho('Write inlet shapefiles', fg='cyan')
    with click.progressbar(groups, length=len(tile_index)) as progress:
        for tile_gid, keys in progress:

            if tile_gid in tiles:
                tile = tiles[tile_gid]
                TileInletSources(tile, keys, areas)

def StreamToFeatureFromSources(row, col, min_drainage):
    """
    DOCME
    """

    ci = [ -1, -1,  0,  1,  1,  1,  0, -1 ]
    cj = [  0,  1,  1,  1,  0, -1, -1, -1 ]

    flow_raster = filename('flow', row=row, col=col)
    acc_raster = filename('acc', row=row, col=col)
    sources = filename('inlet-sources', row=row, col=col)
    output = filename('streams-t-sources', row=row, col=col)

    driver = 'ESRI Shapefile'
    schema = {
        'geometry': 'LineString',
        'properties': [
            ('GID', 'int'),
            ('HEAD', 'int:1'),
            ('ROW', 'int:4'),
            ('COL', 'int:4')
        ]
    }
    crs = fiona.crs.from_epsg(2154)
    options = dict(driver=driver, crs=crs, schema=schema)

    with rio.open(flow_raster) as ds:

        flow = ds.read(1)

        height, width = flow.shape

        def intile(i, j):
            return all([i >= 0, i < height, j >= 0, j < width])

        with rio.open(acc_raster) as ds2:
            streams = np.int16(ds2.read(1) > min_drainage)

        with fiona.open(sources) as fs:
            for feature in fs:

                x, y = feature['geometry']['coordinates']
                i, j = ds.index(x, y)

                while intile(i, j) and streams[i, j] == 0:

                    streams[i, j] = 1
                    direction = flow[i, j]

                    if direction == -1 or direction == 0:
                        break

                    n = int(np.log2(direction))
                    i = i + ci[n]
                    j = j + cj[n]

        with fiona.open(output, 'w', **options) as dst:

            for current, (segment, head) in enumerate(speedup.stream_to_feature(streams, flow)):

                coords = ta.pixeltoworld(np.fliplr(np.int32(segment)), ds.transform, gdal=False)
                dst.write({
                    'type': 'Feature',
                    'geometry': {'type': 'LineString', 'coordinates': coords},
                    'properties': {
                        'GID': current,
                        'HEAD': 1 if head else 0,
                        'ROW': row,
                        'COL': col
                    }
                })

def AggregateStreamsFromSources():
    """
    Aggregate Streams Shapefile
    """

    tile_index = tileindex()
    output = filename('streams-sources')

    driver = 'ESRI Shapefile'
    schema = {
        'geometry': 'LineString',
        'properties': [
            ('GID', 'int'),
            ('HEAD', 'int:1'),
            ('ROW', 'int:4'),
            ('COL', 'int:4')
        ]
    }
    crs = fiona.crs.from_epsg(2154)
    options = dict(driver=driver, crs=crs, schema=schema)

    gid = itertools.count(1)

    with fiona.open(output, 'w', **options) as dst:
        with click.progressbar(tile_index) as progress:
            for row, col in progress:
                with fiona.open(filename('streams-t-sources', row=row, col=col)) as fs:
                    for feature in fs:
                        feature['properties']['GID'] = next(gid)
                        dst.write(feature)