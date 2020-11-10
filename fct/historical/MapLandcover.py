# coding: utf-8

"""
Map multitemporal landcover over axis 

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import os
import glob
import re
from collections import namedtuple
from multiprocessing import Pool
import numpy as np

import click
import rasterio as rio
import fiona
import fiona.crs
from shapely.geometry import asShape
import xarray as xr

from ..tileio import as_window
from ..cli import starcall
from ..config import config
from ..metadata import set_metadata

DatasetParameter = namedtuple('DatasetParameter', [
    'multilandcover', # multilandcover, landcover-hmvt
    'swath_raster', # ax_dgo
    'swath_polygons', # ax_dgo_vector
    'output', # ax_swath_multilandcover_maps
])

def MapSwathLandcover(axis,
        gid,
        bounds,
        multilandcover,
        swath_mask,
        date,
        **kwargs):
    """
    Map landcover on a single date and on a swath
    """

    landcover_raster = config.tileset().filename(multilandcover, axis=axis, idx=date, **kwargs)

    with rio.open(landcover_raster) as ds:
        window = as_window(bounds, ds.transform)
        landcover = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)

    try:
        assert swath_mask.shape == landcover.shape
    except AssertionError:
        click.secho('Error on swath (%d, %d): swath mask and landcover are not the same shape' % (axis, gid), fg='yellow')
        values = np.zeros(landcover.shape, dtype='uint8')
        return values

    if np.sum(swath_mask) == 0:
        click.secho('No data for swath (%d, %d)' % (axis, gid), fg='yellow')
        values = np.zeros(landcover.shape, dtype='uint8')
        return values

    landcover[np.where(~swath_mask)] = 0

    return landcover

def MapMultiTemporalSwathLandcover(axis, gid, bounds, datasets, **kwargs):
    """
    Export multitemporal landcover of a SWATH to netcdf raster format
    """

    subset = config.dataset(datasets.multilandcover).properties['subset']
    template = config.filename(datasets.multilandcover)
    globexpr = template % {'idx': '*'}
    reexpr = template % {'idx': '(.*?)_(.*)'}
    vrts = glob.glob(globexpr)
    indexes = [re.search(reexpr, t).group(1) for t in vrts]

    swath_raster = config.tileset().filename(datasets.swath_raster, axis=axis, **kwargs)
    with rio.open(swath_raster) as ds:
        window = as_window(bounds, ds.transform)
        swath_mask = (ds.read(1, window=window, boundless=True, fill_value=ds.nodata) == gid)
        
        xrange = range(window.col_off, window.col_off+window.width)
        yrange = range(window.row_off, window.row_off+window.height)
        xlist = [ds.xy(1,x)[0] for x in xrange]
        ylist = [ds.xy(y,1)[1] for y in yrange]

    def arguments():
        for date in indexes:

            yield (
                axis,
                gid,
                bounds,
                datasets.multilandcover,
                swath_mask,
                date
            )

    values = np.zeros((len(indexes),*swath_mask.shape), dtype='uint8')
    for idx, args in enumerate(arguments()):
        date_values = MapSwathLandcover(*args)
        values[idx] = date_values

    # Fill nodata dates
    for idx, v in enumerate(values):
        if idx > 0 and v.all() == 255:
            values[idx] = values[idx-1]

    dataset = xr.Dataset({
        'landcover': (('time', 'y', 'x'), values)
        }, 
        coords={
            'x': xlist,
            'y': ylist,
            'time': np.array(indexes, dtype='datetime64')
            })

    output = config.filename(datasets.output, axis=axis, gid=gid, subset=subset, **kwargs)
    dataset.to_netcdf(output, 'w')


def MapLandcover(axis, landcoverset, processes=1, **kwargs):
    """
    Map multitemporal landcover over axis
    """
    
    defaults = dict(
        multilandcover='landcover-hmvt',
        swath_raster='ax_swaths_refaxis',
        swath_polygons='ax_swaths_refaxis_polygons',
        output='ax_swath_multilandcover_maps',
    )

    defaults.update({k: kwargs[k] for k in kwargs.keys() & defaults.keys()})
    datasets = DatasetParameter(**defaults)
    kwargs = {k: kwargs[k] for k in kwargs.keys() - defaults.keys()}

    swath_shapefile = config.filename(datasets.swath_polygons, axis=axis, **kwargs)

    with fiona.open(swath_shapefile) as fs:
        length = len(fs)

    def arguments():

        with fiona.open(swath_shapefile) as fs:
            for feature in fs:

                if feature['properties']['VALUE'] == 0:
                    continue

                gid = feature['properties']['GID']
                geometry = asShape(feature['geometry'])

                yield (
                    MapMultiTemporalSwathLandcover,
                    axis,
                    gid,
                    geometry.bounds,
                    datasets,
                    kwargs
                )

    with Pool(processes=processes) as pool:

        pooled = pool.imap_unordered(starcall, arguments())

        with click.progressbar(pooled, length=length) as iterator:
            for _ in iterator:
                pass