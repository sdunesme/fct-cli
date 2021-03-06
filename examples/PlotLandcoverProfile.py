from fct.config import config
config.default()

from fct.continuity.LateralContinuity import LateralContinuity
from fct.corridor.HeightAboveNearestDrainage import HeightAboveNearestDrainage, HeightAboveTalweg

axis = 3
HeightAboveTalweg(axis)

from fct.tileio import buildvrt, translate

buildvrt('landcover', 'ax_talweg_height', axis=axis)
buildvrt('landcover', 'ax_talweg_distance', axis=axis)

from fct.config import config
config.default()

from fct.swath.LandCoverSwathProfile import LandCoverSwath
from fct.swath.ElevationSwathProfile import SwathProfiles
from fct.metrics.CorridorWidth import (
    CorridorWidth,
    WriteCorridorWidth
)
from fct.metrics.LandCoverWidth import (
    DatasetParameter,
    LandCoverWidth as _LandCoverWidth,
    WriteLandCoverWidth
)
from fct.plotting.PlotCorridor import (
    PlotLandCoverProfile,
    PlotLeftRightContinuityProfile,
    SetupPlot,
    SetupMeasureAxis,
    FinalizePlot
)
import matplotlib as mpl
import matplotlib.pyplot as plt

axis = 3
processes = 5

SwathProfiles(axis, processes=processes)
LandCoverSwath(axis, processes=processes, landcover='landcover-bdt', subset='TOTAL_BDT')
LandCoverSwath(axis, processes=processes, landcover='ax_continuity_variant', variant='CESBIO', subset='CONT_CESBIO')
LandCoverSwath(axis, processes=processes, landcover='ax_continuity_variant', variant='BDT', subset='CONT_BDT')
LandCoverSwath(axis, processes=processes, landcover='ax_continuity_variant', variant='BDT_NOINFRA', subset='CONT_NOINFRA')

width = CorridorWidth(axis)
WriteCorridorWidth(axis, width)

def LandCoverWidth(subset, method, landcover, **kwargs):

    datasets = DatasetParameter(
        landcover=landcover,
        swath_features='ax_swath_polygons',
        swath_data='ax_swath_landcover'
    )
    
    data = _LandCoverWidth(axis, method, datasets, subset=subset, **kwargs)
    # WriteLandCoverWidth(axis, data, output='metrics_lcw_variant', variant=subset)
    return data

def ShowLandCoverProfile(data):

    merged = width.merge(data).sortby(width['measure'])
    
    fig, ax = SetupPlot()
    PlotLandCoverProfile(
        ax,
        merged,
        merged['measure'],
        merged['lcw'].sel(type='total'),
        basis=2,
        window=5)
    SetupMeasureAxis(ax, merged['measure'])
    ax.set_ylabel('Width (m)')
    FinalizePlot(
        fig,
        ax,
        title='Total Landcover Width')

def ShowLeftRightContinuityProfile(data):

    merged = width.merge(data).sortby(width['measure'])

    fig, ax = SetupPlot()
    PlotLeftRightContinuityProfile(
        ax,
        merged,
        merged['measure'],
        merged['lcw'].sel(type='left'),
        merged['lcw'].sel(type='right'),
        window=5)
    SetupMeasureAxis(ax, merged['measure'])
    ax.set_ylabel('Width (m)')
    ax.legend(ncol=2)
    FinalizePlot(
        fig,
        ax,
        title='Left and Right Banks Landcover Width')
    
def Plots(data, variant):

    merged = width.merge(data).sortby(width['measure'])
    
    fig, ax = SetupPlot()
    PlotLandCoverProfile(
        ax,
        merged,
        merged['measure'],
        merged['lcw'].sel(type='total'),
        basis=2,
        window=5)
    SetupMeasureAxis(ax, merged['measure'])
    ax.set_ylabel('Width (m)')
    FinalizePlot(
        fig,
        ax,
        title='Total Landcover Width',
        filename=config.filename('pdf_ax_landcover_profile', axis=axis, variant=variant))

    fig, ax = SetupPlot()
    PlotLeftRightContinuityProfile(
        ax,
        merged,
        merged['measure'],
        merged['lcw'].sel(type='left'),
        merged['lcw'].sel(type='right'),
        window=5)
    SetupMeasureAxis(ax, merged['measure'])
    ax.set_ylabel('Width (m)')
    ax.legend(ncol=2)
    FinalizePlot(
        fig,
        ax,
        title='Left and Right Banks Landcover Width',
        filename=config.filename('pdf_ax_leftright_profile', axis=axis, variant=variant))

# mpl.use('cairo')

# data = LandCoverWidth('TOTAL_BDT', 'total landcover width', landcover='landcover-bdt')
# Plots(data, variant='TOTAL_BDT')

# data = LandCoverWidth('CONT_CESBIO', 'continuous buffer width from river channel')
# Plots(data, variant='CONT_CESBIO')

# data = LandCoverWidth('CONT_BDT', 'continuous buffer width from river channel', landcover='ax_continuity_variant', variant='BDT')
# Plots(data, variant='CONT_BDT')

# data = LandCoverWidth('CONT_NOINFRA', 'continuous buffer width from river channel', landcover='ax_continuity_variant', variant='BDT_NOINFRA')
# Plots(data, variant='CONT_NOINFRA')

LandCoverWidth(
    'TOTAL_BDT',
    'total landcover width',
    landcover='landcover-bdt')

LandCoverWidth(
    'CONT_CESBIO',
    'continuous buffer width from river channel',
    landcover='ax_continuity_variant',
    variant='CESBIO')

LandCoverWidth(
    'CONT_BDT',
    'continuous buffer width from river channel',
    landcover='ax_continuity_variant',
    variant='BDT')

LandCoverWidth(
    'CONT_NOINFRA',
    'continuous buffer width from river channel',
    landcover='ax_continuity_variant',
    variant='BDT_NOINFRA')

from fct.config import config
from fct.metrics.WatershedMetrics import (
    WatershedMetrics,
    WriteWatershedMetrics
)

config.default()
axis = 3

dataset = WatershedMetrics(axis, processes=5)
print(dataset)
WriteWatershedMetrics(axis, dataset)