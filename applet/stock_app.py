"""
This file demonstrates a bokeh applet, which can either be viewed
directly on a bokeh-server, or embedded into a flask application.
See the README.md file in this directory for instructions on running.
"""

import os
import logging
logging.basicConfig(level=logging.DEBUG)

import numpy
import pandas

import bokeh.models as bmodels
import bokeh.plotting as bplotting
import bokeh.properties as bprops
import bokeh.server as bserver
import bokeh.server.utils.plugins as bplugins

# build up list of stock data in the daily folder
data_dir = os.path.join(os.path.dirname(__file__), "daily")
try:
    tickers = os.listdir(data_dir)
except OSError as e:
    print('Stock data not available, see README for download instructions.')
    raise e
tickers = [os.path.splitext(x)[0].split("table_")[-1] for x in tickers]

# cache stock data as dict of pandas DataFrames
pandas_cache = {}


def get_station_data(station):
    fname = os.path.join(data_dir, "K{}.csv".format(station.upper()))
    data = pandas.read_csv(fname, parse_dates=['Date'], index_col=['Date'])
    return data.rename(columns=lambda c: '{}_{}'.format(station, c))


def get_viz_data(ticker1, ticker2):
    if pandas_cache.get((ticker1, ticker2)) is not None:
        return pandas_cache.get((ticker1, ticker2))

    # only append columns if it is the same ticker
    if ticker1 != ticker2:
        data1 = get_station_data(ticker1)
        data2 = get_station_data(ticker2)
        data = data1.join(data2, how='outer')
    else:
        data = get_station_data(ticker1)

    data = data.dropna()
    pandas_cache[(ticker1, ticker2)] = data
    return data


class MetApp(bmodels.widgets.VBox):
    extra_generated_classes = [["MetApp", "MetApp", "VBox"]]
    jsmodel = "VBox"

    # text statistics
    pretext = bprops.Instance(bmodels.widgets.PreText)

    # plots
    plot = bprops.Instance(bmodels.Plot)
    line_plot1 = bprops.Instance(bmodels.Plot)
    line_plot2 = bprops.Instance(bmodels.Plot)
    hist1 = bprops.Instance(bmodels.Plot)
    hist2 = bprops.Instance(bmodels.Plot)

    # data source
    source = bprops.Instance(bmodels.ColumnDataSource)

    # layout boxes
    mainrow = bprops.Instance(bmodels.widgets.HBox)
    histrow = bprops.Instance(bmodels.widgets.HBox)
    statsbox = bprops.Instance(bmodels.widgets.VBox)

    # inputs
    ticker1 = bprops.String(default="SEA")
    ticker2 = bprops.String(default="PDX")
    ticker1_select = bprops.Instance(bmodels.widgets.Select)
    ticker2_select = bprops.Instance(bmodels.widgets.Select)
    input_box = bprops.Instance(bmodels.widgets.VBoxForm)

    def __init__(self, *args, **kwargs):
        super(MetApp, self).__init__(*args, **kwargs)
        self._dfs = {}

    @classmethod
    def create(cls):
        """
        This function is called once, and is responsible for
        creating all objects (plots, datasources, etc)
        """
        # create layout bmodels.widgets
        obj = cls()
        obj.mainrow = bmodels.widgets.HBox()
        obj.histrow = bmodels.widgets.HBox()
        obj.statsbox = bmodels.widgets.VBox()
        obj.input_box = bmodels.widgets.VBoxForm()

        # create input bmodels.widgets
        obj.make_inputs()

        # outputs
        obj.pretext = bmodels.widgets.PreText(text="", width=500)
        obj.make_source()
        obj.make_plots()
        obj.make_stats()

        # layout
        obj.set_children()
        return obj

    def make_inputs(self):

        self.ticker1_select = bmodels.widgets.Select(
            name='ticker1',
            value='SEA',
            options=['SEA', 'PDX', 'SFO', 'LAX', 'BHM', 'ATL']
        )
        self.ticker2_select = bmodels.widgets.Select(
            name='ticker2',
            value='PDX',
            options=['SEA', 'PDX', 'SFO', 'LAX', 'BHM', 'ATL']
        )

    @property
    def selected_df(self):
        pandas_df = self.df
        selected = self.source.selected #['1d'].index
        if selected:
            pandas_df = pandas_df.iloc[selected, :]
        return pandas_df

    def make_source(self):
        self.source = bmodels.ColumnDataSource(data=self.df)

    def line_plot(self, ticker, x_range=None):
        p = bplotting.figure(
            title=ticker,
            x_range=x_range,
            x_axis_type='datetime',
            plot_width=1000, plot_height=200,
            title_text_font_size="10pt",
            tools="pan,wheel_zoom,box_select,reset"
        )
        p.circle(
            'Date', ticker + '_Precip',
            size=2,
            source=self.source,
            nonselection_alpha=0.02
        )
        return p

    def hist_plot(self, ticker):
        global_hist, global_bins = numpy.histogram(self.df[ticker + "_Precip"], bins=50)
        hist, bins = numpy.histogram(self.selected_df[ticker + "_Precip"], bins=50)
        width = 0.7 * (bins[1] - bins[0])
        center = (bins[:-1] + bins[1:]) / 2
        start = global_bins.min()
        end = global_bins.max()
        top = hist.max()

        p = bplotting.figure(
            title="%s hist" % ticker,
            plot_width=500, plot_height=200,
            tools="",
            title_text_font_size="10pt",
            x_range=[start, end],
            y_range=[0, top],
        )
        p.rect(center, hist / 2.0, width, hist)
        return p

    def make_plots(self):
        ticker1 = self.ticker1
        ticker2 = self.ticker2
        p = bplotting.figure(
            title="%s vs %s" % (ticker1, ticker2),
            plot_width=400, plot_height=400,
            tools="pan,wheel_zoom,box_select,reset",
            title_text_font_size="10pt",
        )
        p.circle(ticker1 + "_Precip", ticker2 + "_Precip",
                 size=2,
                 nonselection_alpha=0.02,
                 source=self.source
        )
        self.plot = p

        self.line_plot1 = self.line_plot(ticker1)
        self.line_plot2 = self.line_plot(ticker2, self.line_plot1.x_range)
        self.hist_plots()

    def hist_plots(self):
        ticker1 = self.ticker1
        ticker2 = self.ticker2
        self.hist1 = self.hist_plot(ticker1)
        self.hist2 = self.hist_plot(ticker2)

    def set_children(self):
        self.children = [self.mainrow, self.histrow, self.line_plot1, self.line_plot2]
        self.mainrow.children = [self.input_box, self.plot, self.statsbox]
        self.input_box.children = [self.ticker1_select, self.ticker2_select]
        self.histrow.children = [self.hist1, self.hist2]
        self.statsbox.children = [self.pretext]

    def input_change(self, obj, attrname, old, new):
        if obj == self.ticker2_select:
            self.ticker2 = new
        if obj == self.ticker1_select:
            self.ticker1 = new

        self.make_source()
        self.make_plots()
        self.set_children()
        bplotting.curdoc().add(self)

    def setup_events(self):
        super(MetApp, self).setup_events()
        if self.source:
            self.source.on_change('selected', self, 'selection_change')
        if self.ticker1_select:
            self.ticker1_select.on_change('value', self, 'input_change')
        if self.ticker2_select:
            self.ticker2_select.on_change('value', self, 'input_change')

    def make_stats(self):
        stats = self.selected_df.describe()
        self.pretext.text = str(stats)

    def selection_change(self, obj, attrname, old, new):
        self.make_stats()
        self.hist_plots()
        self.set_children()
        bplotting.curdoc().add(self)

    @property
    def df(self):
        return get_viz_data(self.ticker1, self.ticker2)


# The following code adds a "/bokeh/stocks/" url to the bokeh-server. This URL
# will render this MetApp. If you don't want serve this applet from a Bokeh
# server (for instance if you are embedding in a separate Flask application),
# then just remove this block of code.
@bserver.app.bokeh_app.route("/bokeh/met/")
@bplugins.object_page("met")
def make_stocks():
    app = MetApp.create()
    return app
