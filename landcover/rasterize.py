import os
import subprocess
import tempfile
from functools import wraps
from multiprocessing import Pool

import rasterio as rio
from rasterio import features
import fiona
import fiona.crs
from shapely.geometry import asShape
import click

from fct.config import config
from fct.cli.Decorators import starcall

config.default()
workdir = tempfile.mkdtemp()
print(workdir)

dbcon = 'PG:host=localhost port=5433 dbname=bdt user=postgres password=sigibi'

def extract_sea(bounds):

    return os.path.join(
        '/media/crousson/Backup/TESTS/TuilesVar',
        'SEA_MASK.shp'
    )

def extract_landcover(fun):

    layer = fun.__name__

    @wraps(fun)
    def decorated(bounds):

        minx, miny, maxx, maxy = bounds
        query = fun(minx=minx, miny=miny, maxx=maxx, maxy=maxy)

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

@extract_landcover
def water(**kwargs):
    """
    Water Channel Polygons
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
        SELECT row_number() over() as gid, 0 as landcover, geom FROM water_channel
        WHERE ST_GeometryType(geom) = 'ST_Polygon';
    """

    return query % kwargs

@extract_landcover
def gravels(**kwargs):
    """
    Gravel Bars Polygons
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
        SELECT row_number() over() as gid, 1 as landcover, geom FROM gravels
        WHERE ST_GeometryType(geom) = 'ST_Polygon';
    """

    return query % kwargs

def RasterizeLandCoverTile(tile):

    rasterfile = config.tileset('landcover').tilename(
        'landcover',
        row=tile.row,
        col=tile.col)

    with rio.open(rasterfile) as ds:

        data = ds.read(1)
        profile = ds.profile.copy()
        profile.update(compress='deflate')
        transform = ds.transform

    data[data == 0] = 2

    layers = [
        extract_sea,
        gravels,
        water
    ]

    def shapes(fun):
        """
        Generate Landcover Polygons
        """

        with fiona.open(fun(tile.bounds)) as fs:

            if len(fs) == 0:
                raise StopIteration

            for feature in fs:
                yield feature['geometry'], feature['properties']['landcover']

    for layer in layers:

        try:
            features.rasterize(shapes(layer), out=data, transform=transform)
        except RuntimeError:
            pass

    with rio.open(rasterfile, 'w', **profile) as dst:
        dst.write(data, 1)

def setup(*args):

    global workdir
    workdir = tempfile.mkdtemp()
    print(workdir)

def RasterizeLandCover(processes=1, **kwargs):

    tileindex = config.tileset('landcover').tileindex

    arguments = [
        (RasterizeLandCoverTile, tile, kwargs)
        for tile in tileindex.values()
    ]

    with Pool(processes=processes, initializer=setup) as pool:

        pooled = pool.imap_unordered(starcall, arguments)

        with click.progressbar(pooled, length=len(arguments)) as iterator:
            for _ in iterator:
                pass

def SeaMask():

    coastal_tiles = [
        (8, 5),
        (8, 6),
        (8, 7),
        (7, 6),
        (7, 7),
        (7, 8)
    ]

    driver = 'ESRI Shapefile'
    crs = fiona.crs.from_epsg(2154)
    schema = {
        'geometry': 'Polygon',
        'properties': [
            ('landcover', 'int:2')
        ]
    }
    options = dict(driver=driver, crs=crs, schema=schema)

    output = os.path.join(
        '/media/crousson/Backup/TESTS/TuilesVar',
        'SEA_MASK.shp'
    )

    with fiona.open(output, 'w', **options) as fst:

        for row, col in coastal_tiles:

            filename = config.tileset('landcover').tilename('landcover', row=row, col=col)
            with rio.open(filename) as ds:

                data = ds.read(1)
                mask = (data == 0)

                polygons = features.shapes(
                    data,
                    mask,
                    connectivity=8,
                    transform=ds.transform)

                for polygon, landcover in polygons:

                    geom = asShape(polygon).buffer(0.0)
                    feature = {
                        'geometry': geom.__geo_interface__,
                        'properties': {
                            'landcover': int(landcover)
                        }
                    }
                    
                    fst.write(feature)
