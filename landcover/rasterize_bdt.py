# coding: utf-8

"""
Calculate landcover raster layer
from BD Topo and RPG vector sources

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import os
import subprocess
from functools import wraps
from multiprocessing import Pool
import tempfile

import numpy as np

import click
import rasterio as rio
from rasterio import features
import fiona

from fct.config import config
from fct.cli.Decorators import starcall
from fct.tileio import as_window
from fct import __version__ as version


workdir = tempfile.mkdtemp()
print(workdir)
dbcon = 'PG:host=localhost port=5433 dbname=bdt user=postgres password=sigibi'

# def sea_mask(*args):

#     return os.path.join(
#         '/media/crousson/Backup/TESTS/TuilesVar',
#         'SEA_MASK_GPK.shp'
#     )

def landcover_layer(value):

    def decorate(fun):

        layer = fun.__name__

        @wraps(fun)
        def decorated(bounds, workdir, padding=10.0):

            minx, miny, maxx, maxy = bounds
            query = fun(
                minx=minx-padding,
                miny=miny-padding,
                maxx=maxx+padding,
                maxy=maxy+padding,
                landcover=value)

            with open(os.path.join(workdir, '%s.sql' % layer), 'w') as fp:
                fp.write(query)

            output = os.path.join(workdir, '%s.shp' % layer)

            subprocess.run([
                'ogr2ogr',
                '-f', 'ESRI Shapefile',
                '-a_srs', 'EPSG:2154',
                '-sql', '@' + os.path.join(workdir, '%s.sql' % layer),
                output,
                dbcon], check=True)

            return output

        return decorated

    return decorate

@landcover_layer(0)
def water(**kwargs):
    """
    Surface Water: River, Lake, Pond, ...
    LandCover Class = 0
    """

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        water_channel AS (
            SELECT
                persistance,
                (ST_Dump(
                    ST_Intersection(
                        ST_Force2D(a.geom),
                        (SELECT geom FROM tile)))).geom as geom
            FROM hydrographie.surface_hydrographique a
            WHERE ST_Intersects(a.geom, (SELECT geom FROM tile))
              AND persistance = 'Permanent'
        )
        SELECT row_number() over() as gid, %(landcover)d as landcover, geom FROM water_channel
        WHERE ST_GeometryType(geom) = 'ST_Polygon';
    """

    return query % kwargs

@landcover_layer(1)
def gravels(**kwargs):
    """
    Gravel Bars
    LandCover Class = 1
    """

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        gravels AS (
            SELECT
                persistance,
                (ST_Dump(
                    ST_Intersection(
                        ST_Force2D(a.geom),
                        (SELECT geom FROM tile)))).geom as geom
            FROM hydrographie.surface_hydrographique a
            WHERE ST_Intersects(a.geom, (SELECT geom FROM tile))
              AND persistance = 'Intermittent'
        )
        SELECT row_number() over() as gid, %(landcover)d as landcover, geom FROM gravels
        WHERE ST_GeometryType(geom) = 'ST_Polygon';
    """

    return query % kwargs

@landcover_layer(2)
def open_natural(**kwargs):
    """
    Open, Natural Areas
    LandCover Class = 2
    """

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        foret AS (
            SELECT geom
            FROM ocs.zone_de_vegetation a
            WHERE  st_intersects(geom, (SELECT geom FROM tile))
               AND nature IN (
                    'Haie',
                    'Lande ligneuse',
                    'Forêt ouverte',
                    'Zone arborée'
                )
        ),
        dilatation AS (
            SELECT st_buffer(geom, 10) AS geom
            FROM foret
        ),
        erosion AS (
            SELECT st_buffer(st_union(geom), -10) AS geom
            FROM dilatation
        ),
        clip AS (
            SELECT st_intersection(geom, (SELECT geom FROM tile)) AS geom
            FROM erosion
        ),
        parts AS (
            SELECT (st_dump(geom)).geom
            FROM clip
        )
        SELECT row_number() over() AS gid, %(landcover)d AS landcover, geom
        FROM parts
        WHERE ST_GeometryType(geom) = 'ST_Polygon';
    """

    return query % kwargs

@landcover_layer(3)
def forest(**kwargs):
    """
    Forest and Wooded Areas
    Landcover Class = 3
    """

        #     dilatation AS (
        #     SELECT st_buffer(geom, 10) AS geom
        #     FROM foret
        # ),
        # erosion AS (
        #     SELECT st_buffer(st_union(geom), -10) AS geom
        #     FROM dilatation
        # ),

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        foret AS (
            SELECT geom
            FROM ocs.zone_de_vegetation a
            WHERE st_intersects(geom, (SELECT geom FROM tile))
              AND nature IN (
                'Bois',
                'Peupleraie',
                'Forêt fermée mixte',
                'Forêt fermée de feuillus',
                'Forêt fermée de conifères'
              )
        ),
        clip AS (
            SELECT st_intersection(geom, (SELECT geom FROM tile)) AS geom
            FROM foret
        ),
        parts AS (
            SELECT (st_dump(geom)).geom
            FROM clip
        )
        SELECT row_number() over() AS gid, %(landcover)d as landcover, geom
        FROM parts
        WHERE ST_GeometryType(geom) = 'ST_Polygon';
    """

    return query % kwargs

@landcover_layer(4)
def grassland(**kwargs):
    """
    Grassland, Pasture
    Landcover Class = 4
    """

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        prairie AS (
            SELECT (st_dump(safe_intersection(st_makevalid(a.geom), (SELECT geom FROM tile), 0.5))).geom AS geom
            FROM rpg.parcelles_graphiques a
            WHERE st_intersects(a.geom, (SELECT geom FROM tile))
                  AND (a.code_group IN ('17', '18'))
        ),
        dilatation AS (
            SELECT st_buffer(geom, 5) AS geom
            FROM prairie
        ),
        erosion AS (
            SELECT st_buffer(st_union(geom), -5) AS geom
            FROM dilatation
        ),
        parts AS (
            SELECT (st_dump(geom)).geom
            FROM erosion
        )
        SELECT row_number() over() AS gid, %(landcover)d as landcover, geom
        FROM parts;
    """

    return query % kwargs

@landcover_layer(5)
def cropland(**kwargs):
    """
    Crops, Vineyard, Orchard,
    Most intensive forms of agriculture
    Landcover Class = 5
    """

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        prairie AS (
            SELECT (st_dump(safe_intersection(st_makevalid(a.geom), (SELECT geom FROM tile), 0.5))).geom AS geom
            FROM rpg.parcelles_graphiques a
            WHERE st_intersects(a.geom, (SELECT geom FROM tile))
                  AND a.code_group NOT IN ('17', '18')
        ),
        dilatation AS (
            SELECT st_buffer(geom, 5) AS geom
            FROM prairie
        ),
        erosion AS (
            SELECT st_buffer(st_union(geom), -5) AS geom
            FROM dilatation
        ),
        parts AS (
            SELECT (st_dump(geom)).geom
            FROM erosion
        )
        SELECT row_number() over() AS gid, %(landcover)d as landcover, geom
        FROM parts;
    """

    return query % kwargs

@landcover_layer(6)
def diffuse_urban(**kwargs):
    """
    Forest and Wooded Areas
    Landcover Class = 3
    """

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        bati AS (
            SELECT t.geom AS geom FROM bati.batiment t WHERE st_intersects(geom, (SELECT geom FROM tile))
            UNION SELECT t.geom AS geom FROM bati.construction_surfacique t WHERE st_intersects(geom, (SELECT geom FROM tile))
            UNION SELECT t.geom AS geom FROM bati.cimetiere t WHERE st_intersects(geom, (SELECT geom FROM tile))
            UNION SELECT t.geom AS geom FROM bati.reservoir t WHERE st_intersects(geom, (SELECT geom FROM tile))
            UNION SELECT t.geom AS geom FROM bati.terrain_de_sport t WHERE st_intersects(geom, (SELECT geom FROM tile))
            UNION SELECT t.geom AS geom FROM transport.aerodrome t WHERE st_intersects(geom, (SELECT geom FROM tile))
        ),
        dilatation AS (
            SELECT st_buffer(geom, 20) AS geom
            FROM bati
        ),
        erosion AS (
            SELECT st_buffer(st_union(geom), -20) AS geom
            FROM dilatation
        ),
        clip AS (
            SELECT st_intersection(geom, (SELECT geom FROM tile)) AS geom
            FROM erosion
        ),
        parts AS (
            SELECT (st_dump(geom)).geom
            FROM clip
        )
        SELECT row_number() over() AS gid, %(landcover)d as landcover, removeHoles(geom, 500) as geom
        FROM parts
        WHERE ST_GeometryType(geom) = 'ST_Polygon';
    """

    return query % kwargs

@landcover_layer(7)
def dense_urban(**kwargs):
    """
    Built environment, dense urban areas
    Landcover Class = 7
    """

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        bati AS (
            SELECT t.geom AS geom FROM bati.batiment t WHERE st_intersects(geom, (SELECT geom FROM tile))
            UNION SELECT t.geom AS geom FROM bati.construction_surfacique t WHERE st_intersects(geom, (SELECT geom FROM tile))
            UNION SELECT t.geom AS geom FROM bati.cimetiere t WHERE st_intersects(geom, (SELECT geom FROM tile))
            UNION SELECT t.geom AS geom FROM bati.reservoir t WHERE st_intersects(geom, (SELECT geom FROM tile))
        ),
        dilatation AS (
            SELECT st_buffer(geom, 20.0) AS geom
            FROM bati
        ),
        erosion AS (
            SELECT st_buffer(st_union(geom), -15.0) AS geom
            FROM dilatation
        ),
        clip AS (
            SELECT st_intersection(geom, (SELECT geom FROM tile)) AS geom
            FROM erosion
        ),
        parts AS (
            SELECT (st_dump(geom)).geom
            FROM clip
        )
        SELECT row_number() over() AS gid, %(landcover)d as landcover, removeHoles(geom, 500) as geom
        FROM parts
        WHERE ST_GeometryType(geom) = 'ST_Polygon';
    """

    return query % kwargs

@landcover_layer(8)
def infrastructures(**kwargs):
    """
    Infrastructures
    Landcover Class = 8
    """

    query = """
        WITH
        tile AS (
            SELECT ST_SetSRID('BOX(%(minx)f %(miny)f, %(maxx)f %(maxy)f)'::box2d, 2154) AS geom
        ),
        route AS (
            SELECT st_intersection(st_buffer(r.geom, r.largeur_de_chaussee/2 + 3.0), (SELECT geom FROM tile)) as geom
            FROM transport.troncon_de_route r
            WHERE
                st_intersects(r.geom, (SELECT geom FROM tile))
                AND r.nature NOT IN (
                    'Sentier',
                    'Escalier',
                    'Chemin',
                    'Bac ou liaison maritime',
                    'Route empierrée',
                    'Piste cyclable')
        ),
        voie_ferree AS (
            SELECT st_intersection(st_buffer(r.geom,
                CASE
                    WHEN r.nature = 'LGV' THEN 15.0
                    WHEN r.nature = 'Voie ferrée principale' AND r.nombre_de_voies = 2 THEN 7.50
                    ELSE 3.0
                END), (SELECT geom FROM tile)) as geom
            FROM transport.troncon_de_voie_ferree r
            WHERE st_intersects(r.geom, (SELECT geom FROM tile))
        ),
        infra AS (
            SELECT geom FROM route
            UNION ALL SELECT geom FROM voie_ferree
            UNION SELECT t.geom AS geom FROM transport.aerodrome t WHERE st_intersects(geom, (SELECT geom FROM tile))
        ),
        parts AS (
            SELECT (st_dump(st_union(geom))).geom
            FROM infra
        )
        SELECT row_number() over() AS gid, %(landcover)d as landcover, geom
        FROM parts;
    """

    return query % kwargs

def MkBaseLandCoverTile(tile, window_t):

    landcover_raster = config.datasource('landcover').filename
    mapping_file = config.datasource('landcover-mapping').filename

    headers = None
    mapping = dict()

    with open(mapping_file) as fp:
        for line in fp:

            x = line.strip().split(',')

            if headers is None:
                headers = x
            else:
                mapping[int(x[1])] = int(x[2])

    def reclass(data, src_nodata, dst_nodata):

        out = np.zeros_like(data, dtype='uint8')

        for k, v in mapping.items():
            out[data == k] = v

        out[data == src_nodata] = dst_nodata

        return out

    with rio.open(landcover_raster) as ds:

        profile = ds.profile.copy()

        window = as_window(tile.bounds, ds.transform)

        height = window_t.height
        width = window_t.width

        data = ds.read(
            1,
            window=window,
            boundless=True,
            fill_value=ds.nodata,
            out_shape=(height, width))

        data = reclass(data, ds.nodata, 255)

        return data, profile

def RasterizeBDTopoLayer(data, tile, transform, layer):

    # layers = [
    #     extract_sea,
    #     gravels,
    #     water
    # ]

    def shapes(fun):
        """
        Generate Landcover Polygons
        """

        with fiona.open(fun(tile.bounds, workdir)) as fs:

            if len(fs) == 0:
                raise StopIteration

            for feature in fs:
                yield feature['geometry'], feature['properties']['landcover']

    # for layer in layers:

    try:
        features.rasterize(shapes(layer), out=data, transform=transform)
    except RuntimeError:
        pass

def RasterizeLandCoverTile(tile, **kwargs):

    # config.default()

    template_raster = config.datasource('dem').filename

    output = config.tileset().tilename(
        'landcover-bdt',
        row=tile.row,
        col=tile.col)

    with rio.open(template_raster) as template:

        window_t = as_window(tile.bounds, template.transform)
        it = window_t.row_off
        jt = window_t.col_off
        height = window_t.height
        width = window_t.width

        data, profile = MkBaseLandCoverTile(tile, window_t)
        # CESBIO Water -> Open Natural
        data[data == 0] = 2

        transform = template.transform * \
            template.transform.translation(jt, it)

        # RasterizeBDTopoLayer(data, tile, transform, sea_mask)
        RasterizeBDTopoLayer(data, tile, transform, diffuse_urban)
        RasterizeBDTopoLayer(data, tile, transform, open_natural)
        RasterizeBDTopoLayer(data, tile, transform, grassland)
        RasterizeBDTopoLayer(data, tile, transform, cropland)
        RasterizeBDTopoLayer(data, tile, transform, forest)
        RasterizeBDTopoLayer(data, tile, transform, dense_urban)

        data = features.sieve(data, 50, connectivity=4)

        RasterizeBDTopoLayer(data, tile, transform, infrastructures)
        RasterizeBDTopoLayer(data, tile, transform, gravels)
        RasterizeBDTopoLayer(data, tile, transform, water)

        profile.update(
            height=height,
            width=width,
            nodata=255,
            dtype='uint8',
            transform=transform,
            compress='deflate'
        )

        with rio.open(output, 'w', **profile) as dst:
            dst.write(data, 1)

def setup(*args):

    global workdir
    workdir = tempfile.mkdtemp()
    print(workdir)

def RasterizeLandCover(processes=1, **kwargs):

    tileindex = config.tileset().tileindex

    arguments = [
        (RasterizeLandCoverTile, tile, kwargs)
        for tile in tileindex.values()
    ]

    with Pool(processes=processes, initializer=setup) as pool:

        pooled = pool.imap_unordered(starcall, arguments)

        with click.progressbar(pooled, length=len(arguments)) as iterator:
            for _ in iterator:
                pass

@click.command()
@click.option('--processes', '-j', default=1, help="Execute j parallel processes")
def cli(processes):
    """
    Calculate landcover raster layer
    """

    config.default()
    tileset = config.tileset()

    click.secho('Command        : %s' % 'rasterize landcover', fg='green')
    click.secho('FCT version    : %s' % version)
    click.secho('Tileset        : %s' % tileset.name)
    click.secho('# of tiles     : %d' % len(tileset))
    if processes > 1:
        click.secho('Run %d parallel processes' % processes, fg='yellow')

    RasterizeLandCover(processes)

if __name__ == '__main__':
    cli()
