# coding: utf-8

"""
Simplify swath polygons

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import fiona
from rastachimp import simplify_dp, smooth_chaikin
from shapely.geometry import asShape
from ..config import config

# def _simplify_dp_smooth(faces, edges, distance, iterations, keep_border=False):

#     edges_simpl = _simplify_dp_edges(faces, edges, distance, keep_border)
#     return _smooth_chaikin_edges(faces, edges_simpl, iterations, keep_border)

# def simplify_dp_smooth(features, distance, iterations, keep_border=False):
#     """
#     Simplify polygon features using the Douglas-Peucker method.
#     This op simplifies edges shared by multiple polygons in the same way. It will
#     also prevent edges from crossing each other.
#     """

#     simpl_features = apply_topological_op(
#         features, _simplify_dp_smooth, distance=distance, iterations=iterations, keep_border=keep_border
#     )

#     # remove degenerate polygons (no area)
#     f_simpl_features = []
#     for f in simpl_features:
#         # if polgygon is degenerate: This will make it empty
#         # if mulitp: It will remove degenerate member polygons
#         geom = f[0].buffer(0)
#         if geom.is_empty:
#             # degenerate
#             continue
#         f_simpl_features.append(set_geom(f, geom))

#     return f_simpl_features

def SimplifySwathPolygons(axis, distance, iterations):
    """
    Simplify (Douglas-Peucker) and smooth (Chaikin) swath polygons
    preserving shared boundaries
    """

    polygon_shapefile = config.filename('ax_valley_swaths_polygons', axis=axis)
    output = config.filename('ax_swath_polygons_vb_simplified', axis=axis)

    with fiona.open(polygon_shapefile) as fs:

        features = [
            (asShape(f['geometry']), f['id'])
            for f in fs
            if f['properties']['VALUE'] == 2
        ]

    simplified = simplify_dp(
        features,
        distance,
        keep_border=False)

    if iterations > 0:

        simplified = smooth_chaikin(
            simplified,
            iterations,
            keep_border=False)

    with fiona.open(polygon_shapefile) as fs:

        options = dict(driver=fs.driver, crs=fs.crs, schema=fs.schema)

        with fiona.open(output, 'w', **options) as dst:

            for geometry, fid in simplified:

                feature = fs.get(fid)
                feature.update(geometry=geometry.__geo_interface__)
                dst.write(feature)