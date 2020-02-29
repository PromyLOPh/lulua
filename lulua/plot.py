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

import sys, argparse, json, unicodedata, pickle, logging, math
from operator import itemgetter
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, LinearAxis, Range1d
from bokeh.embed import json_item

from .layout import *
from .keyboard import defaultKeyboards
from .util import limit, displayText
from .writer import Writer
from .carpalx import Carpalx, models

def letterfreq (args):
    """ Map key combinations to their text, bin it and plot sorted distribution """

    # show unicode class "letters other" only
    whitelistCategory = {'Lo'}

    stats = pickle.load (sys.stdin.buffer)

    # XXX: add layout to stats?
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts[args.layout].specialize (keyboard)


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

    xdata = []
    xlabel = []
    ydata = []
    ydataAbs = []
    ydataCumAbs = []
    ydataCumRel = []

    cumSum = combinationTotal
    for i, (k, v) in enumerate (sorted (binned.items (), key=itemgetter (1))):
        xdata.append (i)
        xlabel.append (k)
        ydata.append (v/combinationTotal)
        ydataAbs.append (v)

        # cumulative
        ydataCumAbs.append (cumSum)
        ydataCumRel.append (cumSum/combinationTotal)
        cumSum -= v

    source = ColumnDataSource(data=dict(x=xdata, letters=xlabel, rel=ydata, abs=ydataAbs, cum=ydataCumAbs, cumRel=ydataCumRel))
    p = figure(
            plot_width=1000,
            plot_height=500,
            x_range=xlabel,
            y_range=(0, 1),
            sizing_mode='scale_both',
            tooltips=[('frequency', '@rel'), ('cumulative', '@cumRel'), ('count', '@abs')],
            )
    p.line ('letters', 'cumRel', source=source, line_width=2)

    p.extra_y_ranges = {"single": Range1d (0, max (ydata))}
    p.vbar(x='letters', width=0.5, top='rel', color="#dc322f", source=source, y_range_name='single')
    p.add_layout(LinearAxis(y_range_name="single"), 'right')

    # styling
    p.xgrid.grid_line_color = None
    p.xaxis.major_label_text_font_size = "1.5em"
    p.xaxis.major_label_text_font_size = "1.5em"
    p.xaxis.major_label_text_font = 'IBM Plex Sans Arabic'
    p.yaxis.major_label_text_font = 'IBM Plex Sans Arabic'
    # no border fill
    p.border_fill_color = None
    p.background_fill_alpha = 0.5

    json.dump (json_item (p), sys.stdout)

    return 0

def triadfreq (args):
    """ Dump triad frequency stats to stdout """
    sorter = dict (
        weight=lambda x: x['weight'],
        effort=lambda x: x['effort'].effort,
        # increase impact of extremely “bad” triads using math.pow
        combined=lambda x: (x['weight']/weightSum)*math.pow (x['effort'].effort, 2)
        )
    def noLimit (l, n):
        yield from l
    limiter = limit if args.limit > 0 else noLimit

    stats = pickle.load (sys.stdin.buffer)

    # XXX: add layout to stats?
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts[args.layout].specialize (keyboard)
    writer = Writer (layout)

    # letter-based binning, in case multiple buttons are mapped to the same
    # letter.
    binned = defaultdict (lambda: dict (weight=0, effort=Carpalx (models['mod01'], writer), textTriad=None))
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
    topTriadsWeight = 0
    for data in sorted (binned.values (), key=lambda x: x['weight'], reverse=True):
        if topTriadsWeight < weightSum*args.cutoff:
            topTriads.append (data)
            topTriadsWeight += data['weight']

    logging.info (f'{len (topTriads)}/{len (stats["triads"].triads)} triads '
            f'contribute to {args.cutoff*100}% of the typing')

    # final output
    sortByEffort = sorted (iter (topTriads), key=sorter[args.sort], reverse=args.reverse)
    for data in limiter (sortByEffort, args.limit):
        print (''.join (map (displayText, data['textTriad'])), data['weight'], data['effort'].effort)

    return 0

