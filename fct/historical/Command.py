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
from .MergeMultitemporalDataset import MergeMultitemporalDataset
# pylint: disable=import-outside-toplevel,unused-argument

@fct_entry_point
def cli(env):
    """
    Multi-temporal datasources processing module
    """

@fct_command(cli)
@arg_axis
@click.option('--landcoverset', '-lc', default='landcover-hmvt', help='landcover multidataset')
@click.option('--dataset', '-ds', default='metrics_lcw_variant', help='dataset to merge')
def merge_landcover(axis, landcoverset='landcover-hmvt', dataset='metrics_lcw_variant'):
    """
    Merge multiple landcover netcdf profiles
    """

    if not config.dataset(landcoverset).properties['multitemporal']:
        click.secho('Merging multiple landcover is only available for multitemporal landcover datasets', fg='yellow')
        return

    if dataset=='swath_landcover':
        output_dataset = 'swath_multilandcover'
    elif dataset=='metrics_lcw_variant':
        output_dataset = 'multimetrics_lcw_variant'

    MergeMultitemporalDataset(axis, landcoverset, dataset, output_dataset)
    