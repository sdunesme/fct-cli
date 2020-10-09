# coding: utf-8

"""
MultiLandCover Tiles Extraction

***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 3 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
from multiprocessing import Pool
import numpy as np

import click
import rasterio as rio
import fiona

from ..cli import starcall
from ..config import config
from ..tileio import as_window
from ..metrics import LandCover

def MkMultiLandCoverTiles(processes=1, multilandcoverset="landcover-hmvt", **kwargs):
    tiles = config.tileset().tileindex
    datasources = config.datasource('landcover').datasources
    # indexes = [datasources.get(key).idx for key in datasources.keys()]

    for ds in datasources:
        click.echo('Extracting tiles for %s datasource' % ds)
        arguments = [(LandCover.MkLandCoverTile, tile, multilandcoverset, ds, kwargs) for tile in tiles.values()]

        with Pool(processes=processes) as pool:

            pooled = pool.imap_unordered(starcall, arguments)

            with click.progressbar(pooled, length=len(arguments)) as iterator:
                for _ in iterator:
                    pass

