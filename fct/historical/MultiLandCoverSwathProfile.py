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

def MergeMultiLandCoverSwathProfiles(axis, landcoverset, **kwargs):
    template = config.filename(landcoverset)
    subset = config.dataset(landcoverset).properties['subset']
    globexpr = template % {'idx': '*'}
    reexpr = template % {'idx': '(.*?)_(.*)'}
    vrts = glob.glob(globexpr)
    indexes = [re.search(reexpr, t).group(1) for t in vrts]
    subsets = ["%s_%s" % (subset, idx) for idx in indexes]
    
    inputs_filenames = [config.filename('swath_landcover', axis=axis, subset=s) for s in subsets]
    inputs = [xr.open_dataset(f) for f in inputs_filenames]
    dates = [int(idx) for idx in indexes]

    dataset = xr.concat(inputs, dim='date')
    dataset['date'] = dates

    # set_metadata(dataset, 'swath_multilandcover')

    dataset.attrs['source'] = vrts

    output = config.filename('swath_multilandcover', axis=axis, subset=subset, **kwargs)
    dataset.to_netcdf(output, 'w')

    return dataset