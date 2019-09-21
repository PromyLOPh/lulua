# Copyright (c) 2019 lulua contributors
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys, argparse, json, unicodedata, pickle, logging
from operator import itemgetter
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
from bokeh.embed import json_item

from .layout import *
from .keyboard import defaultKeyboards
from .util import limit
from .writer import Writer
from .carpalx import Carpalx, model01

def letterfreq (args):
    """ Map key combinations to their text, bin it and plot sorted distribution """

    # show unicode class "letters other" only
    whitelistCategory = {'Lo'}

    stats = pickle.load (sys.stdin.buffer)

    # XXX: add layout to stats?
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts[args.layout].specialize (keyboard)

    xdata = []
    xlabel = []
    ydata = []
    ydataAbs = []

    # letter-based binning, in case multiple buttons are mapped to the same
    # letter.
    binned = defaultdict (int)
    for k, v in stats['simple'].combinations.items ():
        # assuming multiple characters have the same category
        text = layout.getText (k)
        category = unicodedata.category (text[0])
        if category in whitelistCategory:
            binned[text] += v
    combinationTotal = sum (binned.values ())
    logging.info (f'total binned combinations {combinationTotal}')

    for i, (k, v) in enumerate (sorted (binned.items (), key=itemgetter (1))):
        xdata.append (i)
        xlabel.append (k)
        ydata.append (v/combinationTotal*100)
        ydataAbs.append (v)

    source = ColumnDataSource(data=dict(x=xdata, letters=xlabel, rel=ydata, abs=ydataAbs))
    p = figure(plot_width=1000, plot_height=500, x_range=xlabel, sizing_mode='scale_both', tooltips=[('frequency', '@rel%'), ('count', '@abs')])
    p.vbar(x='letters', width=0.5, top='rel', color="#dc322f", source=source)
    p.xgrid.grid_line_color = None
    p.xaxis.major_label_text_font_size = "2em"
    p.xaxis.major_label_text_font_size = "2em"

    json.dump (json_item (p), sys.stdout)

    return 0

def triadfreq (args):
    stats = pickle.load (sys.stdin.buffer)

    # XXX: add layout to stats?
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts[args.layout].specialize (keyboard)
    writer = Writer (layout)

    # letter-based binning, in case multiple buttons are mapped to the same
    # letter.
    binned = defaultdict (lambda: dict (weight=0, effort=Carpalx (model01, writer), textTriad=None))
    weightSum = 0
    for triad, weight in stats['triads'].triads.items ():
        textTriad = tuple (layout.getText (t) for t in triad)
        data = binned[textTriad]
        data['weight'] += weight
        data['effort'].addTriad (triad, weight)
        data['textTriad'] = textTriad
        data['layers'] = tuple (layout.modifierToLayer (x.modifier)[0] for x in triad)
        weightSum += weight

    # triads that contribute to x% of the weight
    topTriads = list ()
    topTriadsCutoff = 0.50
    topTriadsWeight = 0
    for data in sorted (binned.values (), key=lambda x: x['weight'], reverse=True):
        if topTriadsWeight < weightSum*topTriadsCutoff:
            topTriads.append (data)
            topTriadsWeight += data['weight']

    # get top triads (by weight)
    print ('by weight')
    for data in limit (sorted (binned.values (), key=lambda x: x['weight'], reverse=True), 20):
        print (data['textTriad'], data['weight'], data['effort'].effort)

    logging.info (f'{len (topTriads)}/{len (stats["triads"].triads)} triads contribute to {topTriadsCutoff*100}% of the typing')

    print ('by effort')
    # only base layer
    includeBaseLayer = iter (topTriads)
    sortByEffort = sorted (includeBaseLayer, key=lambda x: x['effort'].effort, reverse=True)
    for data in limit (sortByEffort, 20):
        print (data['textTriad'], data['weight'], data['effort'].effort)

    print ('by effort and weight')
    includeBaseLayer = iter (topTriads)
    sortByEffortWeight = sorted (includeBaseLayer, key=lambda x: (x['weight']/weightSum)*x['effort'].effort, reverse=True)
    for data in limit (sortByEffortWeight, 20):
        print (data['textTriad'], data['weight'], data['effort'].effort)

    return 0

