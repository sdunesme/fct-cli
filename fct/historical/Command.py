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

from ..config import config
# pylint: disable=import-outside-toplevel,unused-argument

@fct_entry_point
def cli(env):
    """
    Multi-temporal datasources processing module
    """

@fct_command(cli)
@arg_axis
@click.option('--landcoverset', '-lc', default='landcover-hmvt', help='landcover multidataset')
@click.option('--dataset', '-ds', default='metrics_width_landcover', help='dataset to merge')
def merge_landcover(axis, landcoverset='landcover-hmvt', dataset='metrics_width_landcover'):
    """
    Merge multiple landcover netcdf profiles
    """

    from .DataPreparation import MergeMultitemporalDataset

    if not config.dataset(landcoverset).properties['multitemporal']:
        click.secho('Merging multiple landcover is only available for multitemporal landcover datasets', fg='yellow')
        return

    if dataset=='swath_landcover':
        output_dataset = 'swath_multilandcover'
    elif dataset=='metrics_width_landcover':
        output_dataset = 'metrics_width_multilandcover'

    MergeMultitemporalDataset(axis, landcoverset, dataset, output_dataset)
    
@fct_command(cli)
@arg_axis
@click.option('--landcoverset', '-lc', default='landcover-hmvt', help='landcover multidataset')
@click.option('--dataset', '-ds', default='metrics_width_multilandcover', help='dataset to clean')
def clean_nodata(axis, landcoverset, dataset):
    """
    Remove dates with no data in metrics multilandcover datasets
    """

    from .DataPreparation import RemoveNoData

    RemoveNoData(axis, landcoverset, dataset)

@fct_command(cli)
@arg_axis
@click.option('--landcoverset', '-lc', default='landcover-hmvt', help='landcover multidataset')
@click.option('--processes', '-j', default=1, help="Execute j parallel processes")
def map_landcover(axis, landcoverset, processes):
    """
    Create netcdf file to map corridor historical landcover
    """

    from .MapLandcover import MapLandcover

    MapLandcover(axis, landcoverset, processes)
    
    