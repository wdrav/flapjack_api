import math
import json
import os
import numpy as np
from registry.models import *
from analysis import analysis
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly
from plotly.colors import DEFAULT_PLOTLY_COLORS
import wellfare as wf
import time

# Set of colors to use for plot markers/lines
#palette = DEFAULT_PLOTLY_COLORS
palette = [
    '#1f77b4',  # muted blue
    '#ff7f0e',  # safety orange
    '#2ca02c',  # cooked asparagus green
    '#d62728',  # brick red
    '#9467bd',  # muted purple
    '#8c564b',  # chestnut brown
    '#e377c2',  # raspberry yogurt pink
    '#7f7f7f',  # middle gray
    '#bcbd22',  # curry yellow-green
    '#17becf',   # blue-teal
    '#000000',
    '#ff0000'
]
ncolors = len(palette)

    
def make_traces(
        df, 
        color='blue', 
        mean=False, 
        std=False, 
        normalize=False,
        show_legend_group=False,
        xaxis='x1', yaxis='y1'
    ):
    '''
    Generate trace data for each sample, or mean and std, for the data in df
    '''
    df = df.sort_values('time')
    if len(df)==0:
        return(None)
    traces = []

    if mean:
        grouped_samp = df.groupby('sample__id')
        st = np.arange(df['time'].min(), df['time'].max(), 0.1)
        vals = []
        for id,samp_data in grouped_samp:
            samp_data = samp_data.sort_values('time')
            t = samp_data[xname].values
            val = samp_data[yname].values
            sval = wf.curves.Curve(x=t, y=val)
            vals.append(sval(st))
        vals = np.array(vals)
        meanval = np.nanmean(vals, axis=0)
        stdval = np.nanstd(vals, axis=0)
        traces.append({
            'x': list(st),
            'y': list(meanval),
            'marker': {'color': color},
            'type': 'scatter',
            'mode': 'lines',
            #'xaxis': xaxis,
            #'yaxis': yaxis
        })

        if std:
            x = np.append(st, st[::-1])
            ylower = (mean-std)[::-1]
            yupper = (mean+std)
            y = np.append(yupper, ylower)
            traces.append({
                'x': list(x),
                'y': list(y),
                'marker': {'color': color},
                'type': 'scatter',
                'mode': 'lines',
                'xaxis': xaxis,
                'yaxis': yaxis,
                'fill': 'toself'
            })
    else:
        traces.append({
            'x': list(df['time'].values),
            'y': list(df['value'].values),
            'marker': {'color': color},
            'type': 'scatter',
            'mode': 'markers',
            'xaxis': xaxis,
            'yaxis': yaxis,
        })
    return(traces)




def plot(df, mean=False, std=False, normalize=False, groupby1=None, groupby2=None):
    '''
        Generate plot data for frontend plotly plot generation
    '''
    if len(df)==0:
        return None

    traces = []
    axis = 1
    colors = {}
    colidx = 0
    grouped = df.groupby(groupby1)     
    n_subplots = len(grouped)   
    for name1,g1 in grouped:
        for name2,g2 in g1.groupby(groupby2):
            if name2 not in colors:
                colors[name2] = palette[colidx%ncolors]
                colidx += 1
                show_legend_group = True
            else:
                show_legend_group = False

            traces += make_traces(
                    g2,
                    color=colors[name2], 
                    mean=False, 
                    std=False, 
                    normalize=False,
                    show_legend_group=False,
                    xaxis='x%d'%axis, yaxis='y%d'%axis 
                )  
        axis += 1
    return traces, n_subplots
