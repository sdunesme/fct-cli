# coding: utf-8

"""
Multi-temporal datasources Commands

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import click

from ..cli import (
    fct_entry_point,
    fct_command,
    arg_axis,
    parallel_opt
)

from .MultiLandCover import MkMultiLandCoverTiles
# pylint: disable=import-outside-toplevel,unused-argument

@fct_entry_point
def cli(env):
    """
    Multi-temporal datasources processing module
    """

@fct_command(cli)
@click.option('--processes', '-j', default=1, help="Execute j parallel processes")
@click.option('--landcoverset', '-lc', default='landcover-hmvt', help='landcover multidataset')
def data_landcover(processes=1, landcoverset='landcover-hmvt'):
    """
    Reclass multi-temporal landcover data and create landcover tiles
    """

    MkMultiLandCoverTiles(processes, landcoverset)