# coding: utf-8

"""
MultiLandCover Swath Profile

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import glob
import re

import click
import xarray as xr

from ..config import config

def MergeMultitemporalDataset(axis, landcoverset, input_dataset, output_dataset, **kwargs):

    subset = config.dataset(landcoverset).properties['subset']
    ds = config.dataset(landcoverset)
    indexes = [d.idx for d in config.datasource(ds.properties['subdatasets_from']).datasources.values()]
    
    template = config.filename(landcoverset)
    globexpr = template % {'idx': '*'}
    vrts = glob.glob(globexpr)

    subsets = ["%s_%s" % (subset, idx) for idx in indexes]
    
    inputs_filenames = [config.filename(input_dataset, axis=axis, subset=s, variant=s) for s in subsets]
    inputs = [xr.open_dataset(f) for f in inputs_filenames]
    dates = [int(idx[-4:]) for idx in indexes]

    dataset = xr.concat(inputs, dim='datasource')
    dataset['datasource'] = indexes
    dataset['time'] = ('datasource', dates)

    # set_metadata(dataset, 'swath_multilandcover')

    dataset.attrs['source'] = vrts

    output = config.filename(output_dataset, axis=axis, subset=subset, **kwargs)
    dataset.to_netcdf(output, 'w')

    return dataset

def RemoveNoData(axis, landcoverset, metrics_dataset, **kwargs):
    """
    Remove dates with no data in metrics multilandcover datasets
    """
    subset = config.dataset(landcoverset).properties['subset']
    filename = config.filename(metrics_dataset, axis=axis, subset=subset, **kwargs)
    
    with xr.open_dataset(filename) as input_dataset:
        dataset = input_dataset.load()
 
    with click.progressbar(dataset['datasource'].data) as iterator:
        for d in iterator:
            total = sum(dataset.sel(datasource=d)['buffer_area'].data.flatten())

            if total==0:
                dataset = dataset.drop_sel(datasource=d)

            else:
                for m in dataset['measure'].data:
                    swath_total = sum(dataset.sel(datasource=d, measure=m)['buffer_area'].data.flatten())

                    if swath_total==0:
                        dataset['buffer_area'].loc[dict(datasource=d, measure=m)] = 'nan'
                        dataset['buffer_width'].loc[dict(datasource=d, measure=m)] = 'nan'
    
    dataset.to_netcdf(filename, 'w')
    
    return dataset