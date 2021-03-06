# coding: utf-8

"""
Swath Medial Axis

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
from multiprocessing import Pool

import numpy as np
import xarray as xr
import click

import rasterio as rio
from rasterio import features
import fiona

from ..config import config
from ..tileio import as_window
from ..cli import starcall

def SwathMedialPoints(axis, swid, coordm, bounds, long_length, resolution):

    tileset = config.tileset()
    swath_shapefile = config.filename('ax_swaths_refaxis_polygons', axis=axis)
    # swath_raster = tileset.filename('ax_valley_swaths', axis=axis)
    # measure_raster = tileset.filename('ax_axis_measure', axis=axis)
    distance_raster = tileset.filename('ax_axis_distance', axis=axis)
    hand_raster = tileset.filename('ax_nearest_height', axis=axis)
    valleybottom_raster = config.tileset().filename('ax_valley_mask_refined', axis=axis)

    points = list()

    # with rio.open(swath_raster) as ds:

    #     window = as_window(bounds, ds.transform)
    #     swaths = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)

    with rio.open(distance_raster) as ds:

        window = as_window(bounds, ds.transform)
        distance = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)
        transform = ds.transform * ds.transform.translation(window.col_off, window.row_off)

    with fiona.open(swath_shapefile) as fs:

        def accept(feature):
            return all([
                feature['properties']['AXIS'] == axis,
                feature['properties']['VALUE'] == 2
            ])

        geometries = [
            (f['geometry'], f['properties']['GID']) for f in fs.filter(bbox=bounds)
            if accept(f)
        ]

        if geometries:

            swaths = features.rasterize(
                geometries,
                out_shape=distance.shape,
                transform=transform,
                fill=0,
                dtype='uint32')

        else:

            return points

    # with rio.open(measure_raster) as ds:

    #     window = as_window(bounds, ds.transform)
    #     measure = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)

    if os.path.exists(valleybottom_raster):

        with rio.open(valleybottom_raster) as ds:

            window = as_window(bounds, ds.transform)
            valleybottom = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)
            mask = (swaths == swid) & (valleybottom < 2)

    else:

        with rio.open(hand_raster) as ds:

            window = as_window(bounds, ds.transform)
            hand = ds.read(1, window=window, boundless=True, fill_value=ds.nodata)
            mask = (swaths == swid) & (hand < 10.0)

    # xmin = coordm - 0.5 * long_length
    # xmax = coordm + 0.5 * long_length
    # xbins = np.linspace(xmin, xmax, 5)

    if np.sum(mask) == 0:
        return points

    ymin = np.min(distance[mask])
    ymax = np.max(distance[mask])

    if (ymax - ymin) < 2000.0:
        ybins = np.arange(ymin, ymax + 10.0, 10.0)
    else:
        ybins = np.linspace(ymin, ymax, 200)

    ybinned = np.digitize(distance, ybins)
    y = 0.5*(ybins[1:] + ybins[:-1])

    if len(y) < 2:
        return points

    # unit width of observations
    unit_width = 0.5 * (np.roll(y, -1) - np.roll(y, 1))
    unit_width[0] = y[1] - y[0]
    unit_width[-1] = y[-1] - y[-2]

    # for x0, x1 in zip(xbins[:-1], xbins[1:]):

    #     maskx = (swaths == swid) & (measure >= x0) & (measure < x1) & (hand < 10.0)
    #     density = np.zeros((len(ybins)-1,), dtype='int32')

    #     for i in range(1, len(ybins)):

    #         maski = maskx & (ybinned == i)
    #         density[i-1] = np.sum(maski)

    #     max_density = long_length / resolution**2
    #     clamp = np.minimum(max_density, density) / max_density

    #     yclamp = y[clamp > 0.8]

    #     if yclamp.size > 0:

    #         xk = 0.5 * (x1 + x0)
    #         yk = np.median(yclamp)
    #         points.append((xk, yk)) # TODO get world x, y from xk, yk

    density = np.zeros((len(ybins)-1,), dtype='int32')
    for i in range(1, len(ybins)):

        maski = mask & (ybinned == i)
        density[i-1] = np.sum(maski)

    max_density = long_length / resolution**2
    clamp = np.minimum(max_density*unit_width, density) / max_density
    yclamp = y[clamp > 0.6 * unit_width]

    if yclamp.size > 0:

        xk = coordm
        yk = np.median(yclamp)
        points.append((xk, yk))

    return points

def SwathMedialAxis(axis, processes=1, **kwargs):
    """
    Calculate swath medial axis

    @api    fct-swath:medialaxis

    @input  swath_bounds: ax_valley_swaths_bounds
    @input  reference_axis: ax_refaxis
    @input  swath_raster: ax_valley_swaths
    @input  swath_polygons: ax_valley_swaths_polygons
    @input  mask: ax_valley_mask_refined
    @input  height: ax_nearest_height
    @param  value_is_valid: 2
    @param  max_height: 10.0
    @param  min_slice_width: 10.0
    @param  max_slice_count: 200

    @output medialaxis: ax_valley_medialaxis
    """

    swath_defs = config.filename('ax_swaths_refaxis_bounds', axis=axis)

    long_length = 200.0
    resolution = 5.0

    defs = xr.open_dataset(swath_defs)
    defs.load()
    defs = defs.sortby('measure')

    length = defs['swath'].shape[0]

    def arguments():

        for k in range(length):

            measure = defs['measure'].values[k]
            swid = defs['swath'].values[k]
            bounds = tuple(defs['bounds'].values[k, :])

            # if gid < 314:
            #     continue

            yield (
                SwathMedialPoints,
                axis,
                swid,
                measure,
                bounds,
                long_length,
                resolution,
                kwargs
            )

    all_points = list()

    with Pool(processes=processes) as pool:

        pooled = pool.imap_unordered(starcall, arguments())

        with click.progressbar(pooled, length=length) as iterator:
            for points in iterator:
                all_points.extend(points)

    return np.array(list(sorted(all_points, key=itemgetter(0))), dtype='float32')

def unproject(axis, points):

    refaxis_shapefile = config.filename('ax_refaxis', axis=axis)

    with fiona.open(refaxis_shapefile) as fs:

        assert len(fs) == 1

        for feature in fs:

            coordinates = np.array(
                feature['geometry']['coordinates'],
                dtype='float32')

            # reverse line direction,
            # keep only x and y coords
            coordinates = coordinates[::-1, :2]

            # calculate m coord
            m0 = feature['properties'].get('M0', 0.0)
            m = m0 + np.cumsum(np.linalg.norm(
                coordinates[1:] - coordinates[:-1],
                axis=1))

            m = np.concatenate([[0], m], axis=0)

    transformed = np.zeros_like(points)

    for i, (mi, di) in enumerate(points):

        if np.isnan(di):

            transformed[i] = np.nan
            continue

        for k, mk in enumerate(m[:-1]):

            if mk <= mi < m[k+1]:
                break

        else:

            transformed[i] = np.nan
            continue

        # p0 between vertices k and k+1

        lenk = m[k+1] - mk
        dirk = (coordinates[k+1] - coordinates[k]) / lenk
        pti = coordinates[k] + (mi - mk) * dirk
        xi = pti[0] + di * dirk[1]
        yi = pti[1] - di * dirk[0]

        transformed[i] = (xi, yi)

    return transformed

def ExportSwathMedialAxisToShapefile(axis, transformed):

    refaxis_shapefile = config.filename('ax_refaxis', axis=axis)
    medialaxis_shapefile = config.filename('ax_medialaxis', mod=False, axis=axis)

    with fiona.open(refaxis_shapefile) as fs:

        driver = fs.driver
        crs = fs.crs

    schema = {
        'geometry': 'LineString',
        'properties': [('AXIS', 'int')]
    }

    options = dict(driver=driver, crs=crs, schema=schema)

    with fiona.open(medialaxis_shapefile, 'w', **options) as fst:

        coordinates = transformed[::-1].tolist()
        feature = {
            'geometry': {'type': 'LineString', 'coordinates': coordinates},
            'properties': {'AXIS': axis}
        }

        fst.write(feature)

def test(axis=2):

    # pylint: disable=import-outside-toplevel
    from ..plotting.Command import SetupMeasureAxis, SetupPlot, FinalizePlot

    config.default()
    medialaxis = SwathMedialAxis(axis, processes=6)

    data = xr.Dataset({'dist': ('measure', medialaxis[:, 1])}, coords={'measure': medialaxis[:, 0]})
    smoothed = data.rolling(measure=5, center=True, min_periods=1).mean()
    transformed = unproject(axis, np.column_stack([smoothed.measure, smoothed.dist]))
    ExportSwathMedialAxisToShapefile(axis, transformed[~np.isnan(transformed[:, 1])])

    # plt.plot(smoothed.measure, smoothed.dist)
    # plt.show()

    fig, ax = SetupPlot()
    ax.plot(smoothed.measure, smoothed.dist)
    ax.set_ylabel('Distance to reference axis (m)')
    SetupMeasureAxis(ax, smoothed.measure)
    FinalizePlot(fig, ax, title='Valley medial axis offset')
