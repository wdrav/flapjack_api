# Built in imports.
import json
import asyncio
# Third Party imports.
from channels.exceptions import DenyConnection
from channels.generic.websocket import AsyncWebsocketConsumer
from . import plotting
from analysis.analysis import Analysis 
from analysis.util import *
from registry.util import get_samples, get_measurements
from registry.models import Signal
from plotly.subplots import make_subplots
import plotly
import pandas as pd
import time
import math

group_fields = {
    'Vector': 'Vector',
    'Study': 'Study',
    'Signal': 'Signal',
    'Assay': 'Assay',
    'Media': 'Media', 
    'Strain': 'Strain', 
    'Supplement': 'Supplements'
}

axis_labels = {
    'Velocity': ('Time', 'Velocity'),
    'Expression Rate (direct)': ('Time', 'Rate'),
    'Expression Rate (indirect)': ('Time', 'Rate'),
    'Mean Expression': (None, 'Expression'),
    'Max Expression': (None, 'Expression'),
    'Mean Velocity': (None, 'Velocity'),
    'Max Velocity': (None, 'Velocity'),
    'Induction Curve': ('Concentration', 'Expression'),
    'Kymograph': ('Concentration', 'Time'),
    'Rho': (None, 'Rate'),
    'Alpha': (None, 'Rate')
}

plot_types = {
    'Velocity': 'timeseries',
    'Expression Rate (direct)': 'timeseries',
    'Expression Rate (indirect)': 'timeseries',
    'Mean Expression': 'bar',
    'Max Expression': 'bar',
    'Mean Velocity': 'bar',
    'Max Velocity': 'bar',
    'Rho': 'bar',
    'Alpha': 'bar',
    'Induction Curve': 'induction',
    'Kymograph': 'kymograph'
}

class PlotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        print(self.user)
        await self.accept()
        await self.channel_layer.group_add(
            "asd",
            self.channel_name
        )

    async def plot(self, df, 
                    mean=False, 
                    std=False, 
                    normalize=False, 
                    groupby1=None, 
                    groupby2=None,
                    font_size=10,
                    xlabel='Time',
                    ylabel='Measurement',
                    plot_type='timeseries'):
        '''
            Generate plot data for frontend plotly plot generation
        '''
        n_measurements = len(df)
        if n_measurements == 0:
            return None

        print('plot df ', df, flush=True)

        traces = []
        colors = {}
        colidx = 0
        subplot_index = 0
        groupby1 = group_fields[groupby1]
        groupby2 = group_fields[groupby2]
        grouped = df.groupby(groupby1)     
        n_subplots = len(grouped)
        ncolors = len(plotting.palette)
        progress = 0

        # Compute number of rows and columns
        n_sub_plots = len(grouped)
        rows,cols = plotting.optimal_grid(n_sub_plots)
        
        # Construct subplots
        start = time.time()
        fig = make_subplots(
                            rows=rows, cols=cols,
                            subplot_titles=[name for name,g in grouped],
                            shared_xaxes=True, shared_yaxes=False,
                            vertical_spacing=0.1, horizontal_spacing=0.1
                            ) 
        end = time.time()

        # Add traces to subplots
        print('make_subplots took %g'%(end-start), flush=True)
        for name1,g1 in grouped:
            for name2,g2 in g1.groupby(groupby2):
                # Choose color and whether to show in legend
                if name2 not in colors:
                    colors[name2] = plotting.palette[colidx%ncolors]
                    colidx += 1
                    show_legend_group = True
                else:
                    show_legend_group = False

                # Which position the subplot is in
                row = 1 + subplot_index//cols
                col = 1 + subplot_index%cols

                # Linear axes by default
                xaxis_type = None
                yaxis_type = None

                # Add traces to figure
                if plot_type == 'timeseries':
                    fig = plotting.make_timeseries_traces(
                            fig,
                            g2,
                            color=colors[name2], 
                            mean=mean, 
                            std=std, 
                            normalize=normalize,
                            show_legend_group=show_legend_group,
                            group_name=str(name2),
                            row=row, col=col,
                            xlabel=xlabel,
                            ylabel=ylabel
                        )
                elif plot_type == 'bar':
                    fig = plotting.make_bar_traces(
                            fig,
                            g2,
                            color=colors[name2], 
                            mean=mean, 
                            std=std, 
                            normalize=normalize,
                            show_legend_group=show_legend_group,
                            group_name=str(name2),
                            row=row, col=col,
                            xlabel=groupby2,
                            ylabel=ylabel
                        )
                elif plot_type == 'induction':
                    fig = plotting.make_induction_traces(
                            fig,
                            g2,
                            color=colors[name2], 
                            mean=mean, 
                            std=std, 
                            normalize=normalize,
                            show_legend_group=show_legend_group,
                            group_name=str(name2),
                            row=row, col=col
                        )
                    xaxis_type = 'log'
                elif plot_type == 'kymograph':
                    fig = plotting.make_kymograph_traces(
                            fig,
                            g2,
                            color=colors[name2], 
                            mean=mean, 
                            std=std, 
                            normalize=normalize,
                            show_legend_group=show_legend_group,
                            group_name=str(name2),
                            row=row, col=col,
                            xlabel=xlabel,
                            ylabel=ylabel
                        )
                    xaxis_type = 'log'
                else:
                    print('Unsupported plot type, ', plot_type, flush=True)
                
                # Format axes
                plotting.format_axes(fig, 
                                        row, col, rows, 
                                        xlabel=xlabel, 
                                        ylabel=ylabel, 
                                        font_size=font_size)

                # Update progress bar
                progress += len(g2)
                await self.send(text_data=json.dumps({
                    'type': 'progress_update',
                    'data': {'progress': int(50 + 50 * progress / n_measurements)}
                }))
                await asyncio.sleep(0)
            # Next subplot
            subplot_index += 1
        plotting.layout_screen(fig, xaxis_type=xaxis_type, yaxis_type=yaxis_type, font_size=font_size)
        return fig

    async def run_analysis(self, df, analysis):
        grouped = df.groupby('Sample')
        result_dfs = []
        n_samples = len(grouped)
        progress = 0
        for id,g in grouped:
            result_df = analysis.analyze_data(g)
            result_dfs.append(result_df)
            progress += 1
            await self.send(text_data=json.dumps({
                'type': 'progress_update',
                'data': {'progress': int(50 * progress / n_samples)}
            }))
            await asyncio.sleep(0)
        df = pd.concat(result_dfs)
        return df

    async def generate_data(self, event):
        params = event['params']
        plot_options = params['plotOptions']
        s = get_samples(params)
        signals = params.get('signalIds')
        n_samples = s.count()
        if n_samples > 0:
            # Get measurements to plot/analyze
            df = get_measurements(s, signals)

            # Default axis labels for raw measurements
            xlabel, ylabel = 'Time', 'Measurement'

            # Default plot type for raw measurements
            plot_type = 'timeseries'

            # Run analysis if selected
            analysis_params = params.get('analysis')
            if analysis_params:
                analysis_type = analysis_params['type']
                xlabel, ylabel = axis_labels[analysis_type]
                plot_type = plot_types[analysis_type]
                analysis = Analysis(analysis_params, signals)
                df = await self.run_analysis(df, analysis)

            normalize = plot_options['normalize']
            if normalize and normalize!='None':
                print('normalizing', flush=True)
                print('normalize', normalize, flush=True)
                df = normalize_data(df, normalize, ylabel)

            # Plot figure
            subplots = plot_options['subplots']
            markers = plot_options['markers']
            normalize = plot_options['normalize']
            mean = 'Mean' in plot_options['plot']
            std = 'std' in plot_options['plot']
            fig = await self.plot(df, 
                                groupby1=subplots, 
                                groupby2=markers,
                                mean=mean, std=std,
                                xlabel=xlabel, ylabel=ylabel,
                                plot_type=plot_type,
                                normalize=normalize
                                )
            if fig:
                fig_json = fig.to_json()
            else:
                fig_json = ''
        else:
            print('No samples found for query params', flush=True)
            fig_json = ''
        # Send back traces to plot
        await self.send(text_data=json.dumps({
            'type': 'plot_data',
            'data': {
                'figure': fig_json
            }
        }))
        
    async def receive(self, text_data):
        print(f"Receive. text_data: {text_data}", flush=True)
        data = json.loads(text_data)
        if data['type'] == 'plot':
            await self.generate_data({'params': data['parameters']})

    async def disconnect(self, message):
        await self.channel_layer.group_discard(
            "asd",
            self.channel_name
        )
