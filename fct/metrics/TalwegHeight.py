# coding: utf-8

"""
Talweg depth relative to floodplain/valley floor

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
from operator import itemgetter
import itertools

import numpy as np
from scipy.interpolate import interp1d

import click
import xarray as xr
import rasterio as rio
import fiona

from .. import transform as fct
from .. import speedup
from ..rasterize import rasterize_linestring
from ..config import config
from ..metadata import set_metadata

def InterpolateMissingValues(measures, values, kind='slinear'):
    """
    Interpolate nan data point from other points in longitudinal serie ;
    data points in `values` are expected to be ordered from upstream to downstream
    (or vice versa).
    """

    isnan = np.isnan(values[:, 0])
    notnan = ~isnan

    missing = np.copy(values)

    for k in range(2):
        fun = interp1d(measures[notnan], values[notnan, k], kind=kind, bounds_error=False)
        missing[isnan, k] = fun(measures[isnan])

    return missing

def TalwegHeightBySwathUnit(axis):
    """
    Calculate median talweg height relative to valley floor
    """

    elevation_raster = config.tileset().filename('dem')
    talweg_shapefile = config.filename('ax_talweg', axis=axis)
    swath_bounds = config.filename('ax_valley_swaths_bounds', axis=axis)
    swath_raster = config.tileset().filename('ax_valley_swaths', axis=axis)
    measure_raster = config.tileset().filename('ax_axis_measure', axis=axis)

    # swath => z0, slope

    defs = xr.open_dataset(swath_bounds)
    defs.load()
    defs = defs.sortby('coordm')

    estimates = dict()

    with click.progressbar(defs['label'].values) as iterator:
        for gid in iterator:

            filename = config.filename('ax_swath_elevation', axis=axis, gid=gid)

            if os.path.exists(filename):

                data = np.load(filename, allow_pickle=True)
                z0 = data['z0_valley_floor']
                slope = data['slope_valley_floor']

                if not (np.isnan(z0) or np.isnan(slope)):
                    estimates[gid] = (slope, z0)

    # talweg => vertices (x, y, z, swath, axis m)

    swathid = np.array([])
    coordz = np.array([])
    coordm = np.array([])
    coords = np.array([])
    # coordxy = np.zeros((0, 2), dtype='float32')

    with fiona.open(talweg_shapefile) as fs:
        with click.progressbar(fs, length=len(fs)) as iterator:
            for feature in iterator:

                coordinates = np.array(feature['geometry']['coordinates'], dtype='float32')

                with rio.open(swath_raster) as ds:

                    coordij = fct.worldtopixel(coordinates[:, :2], ds.transform)
                    pixels = list()

                    # we must interpolate segments between vertices
                    # otherwise we may miss out swaths that fit between 2 vertices

                    for a, b in zip(coordij[:-1], coordij[1:]):
                        for i, j in rasterize_linestring(a, b):
                            pixels.append((i, j))

                    segment_xy = fct.pixeltoworld(
                        np.array(pixels, dtype='int32'),
                        ds.transform)

                    # coordxy = np.concatenate([
                    #     coordxy,
                    #     segment_xy
                    # ], axis=0)

                    # calculate s coordinate
                    segment_s = np.cumsum(np.linalg.norm(
                        # segment_xy[:0:-1] - segment_xy[-2::-1],
                        segment_xy[1:] - segment_xy[:-1],
                        axis=1))

                    coords = np.concatenate([
                        coords,
                        [0],
                        segment_s
                    ])

                    segment_swathid = np.array(list(ds.sample(segment_xy, 1)))
                    swathid = np.concatenate([swathid, segment_swathid[:, 0]], axis=0)

                with rio.open(measure_raster) as measure_ds:

                    segment_m = np.array(list(measure_ds.sample(segment_xy, 1)))
                    coordm = np.concatenate([coordm, segment_m[:, 0]], axis=0)

                with rio.open(elevation_raster) as ds:

                    segment_z = np.array(list(ds.sample(segment_xy, 1)))
                    coordz = np.concatenate([coordz, segment_z[:, 0]], axis=0)

    indices = sorted(enumerate(swathid), key=itemgetter(1))
    groups = itertools.groupby(indices, key=itemgetter(1))

    swids = list()
    measures = list()
    heights = list()
    talweg_slopes = list()
    # floodplain_slopes = list()

    for swid, group in groups:

        if swid == 0:
            continue

        elements = np.array([k for k, _ in group])

        Y = ztalweg = coordz[elements]
        X = np.column_stack([
            coords[elements],
            np.ones_like(elements),
        ])

        (talweg_slope, talweg_z0), sqerror_talweg, _, _ = np.linalg.lstsq(X, Y, rcond=None)

        if swid in estimates:

            floodplain_slope, floodplain_z0 = estimates[swid]
            zvalley = floodplain_slope * coordm[elements] + floodplain_z0

            hmedian = np.median(ztalweg - zvalley)
            hmin = np.min(ztalweg - zvalley)

        else:

            # htalweg = -10.0
            hmedian = hmin = np.nan
            floodplain_slope = np.nan

        swathm = defs['coordm'].sel(label=swid).values

        measures.append(swathm)
        swids.append(swid)
        heights.append((hmedian, hmin))
        # floodplain_slopes.append(floodplain_slope)
        talweg_slopes.append(talweg_slope)

    swids = np.array(swids, dtype='uint32')
    measures = np.array(measures, dtype='float32')

    heights = np.array(heights, dtype='float32')
    interpolated = np.isnan(heights[:, 0])
    heights = InterpolateMissingValues(measures, heights)

    talweg_slopes = -100 * np.array(talweg_slopes, dtype='float32')
    # floodplain_slopes = np.array(floodplain_slopes, dtype='float32')

    dataset = xr.Dataset(
        {
            'talweg_height_median': ('measure', heights[:, 0]),
            'talweg_height_min': ('measure', heights[:, 1]),
            'flag_twh_interpolated': ('measure', interpolated),
            'talweg_slope': ('measure', talweg_slopes)
            # 'floodplain_slope': ('measure', floodplain_slopes)
        },
        coords={
            'axis': axis,
            'measure': measures,
            'swath': ('measure', swids),
        }
    )

    # Metadata

    set_metadata(dataset, 'metrics_talweg_height')

    return dataset

def WriteTalwegHeights(axis, dataset):
    """
    Save talweg height data to NetCDF file
    """

    # write to netCDF

    output = config.filename('metrics_talweg_height', axis=axis)

    dataset.to_netcdf(
        output,
        'w',
        encoding={
            'swath': dict(zlib=True, complevel=9),
            'measure': dict(zlib=True, complevel=9, least_significant_digit=0),
            'talweg_height_median': dict(zlib=True, complevel=9, least_significant_digit=1),
            'talweg_height_min': dict(zlib=True, complevel=9, least_significant_digit=1),
            'talweg_slope': dict(zlib=True, complevel=9, least_significant_digit=6),
            # 'floodplain_slope': dict(zlib=True, complevel=9, least_significant_digit=6),
            'flag_twh_interpolated': dict(zlib=True, complevel=9)
        })
