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
    template = config.filename(landcoverset)
    subset = config.dataset(landcoverset).properties['subset']
    globexpr = template % {'idx': '*'}
    reexpr = template % {'idx': '(.*?)_(.*)'}
    vrts = glob.glob(globexpr)
    indexes = [re.search(reexpr, t).group(1) for t in vrts]
    subsets = ["%s_%s" % (subset, idx) for idx in indexes]
    
    inputs_filenames = [config.filename(input_dataset, axis=axis, subset=s, variant=s) for s in subsets]
    inputs = [xr.open_dataset(f) for f in inputs_filenames]
    dates = [int(idx) for idx in indexes]

    dataset = xr.concat(inputs, dim='date')
    dataset['date'] = dates

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
 
    with click.progressbar(dataset['date'].data) as iterator:
        for d in iterator:
            total = sum(dataset.sel(date=d)['buffer_area'].data.flatten())

            if total==0:
                dataset = dataset.drop_sel(date=d)

            else:
                for m in dataset['measure'].data:
                    swath_total = sum(dataset.sel(date=d, measure=m)['buffer_area'].data.flatten())

                    if swath_total==0:
                        dataset['buffer_area'].loc[dict(date=d, measure=m)] = 'nan'
                        dataset['buffer_width'].loc[dict(date=d, measure=m)] = 'nan'
    
    dataset.to_netcdf(filename, 'w')
    
    return dataset