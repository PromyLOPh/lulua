# Copyright (c) 2020 lulua contributors
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

import sys, argparse, logging, pickle
from gettext import GNUTranslations, NullTranslations
from decimal import Decimal

import yaml
from jinja2 import Environment, PackageLoader
from bokeh.resources import CDN as bokehres

from .layout import LEFT, RIGHT, Direction, FingerType

def approx (i, lang='en'):
    """ Get approximate human-readable string for large number """

    units = {'en': ['', 'thousand', 'million', 'billion'],
            'ar': ['', 'ألف', 'مليون', 'مليار']}[lang]
    base = Decimal (1000)
    i = Decimal (i)
    while round (i, 1) >= base and len (units) > 1:
        i /= base
        units.pop (0)
    return round (i, 1), units[0]

def numspace (s):
    """ Replace ordinary spaces with unicode FIGURE SPACE """
    return s.replace (' ', '\u2007')

def arabnum (s):
    """
    Convert number to arabic-indic ordinals.

    Granted, we could use setlocale and do proper formatting, but who has an
    arabic locale installed…?
    """
    m = {'0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤', '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩', ',': '٬', '.': '٫'}
    return ''.join (map (lambda x: m.get (x, x), s))

def render ():
    parser = argparse.ArgumentParser(description='Create lulua report.')
    parser.add_argument('-c', '--corpus', nargs='+', metavar='FILE', help='Corpus metadata files')
    parser.add_argument('-l', '--layoutstats', nargs='+', metavar='FILE', help='Layout statistics files')
    logging.basicConfig (level=logging.INFO)
    args = parser.parse_args()

    env = Environment (
            loader=PackageLoader (__package__, 'data/report'),
            )
    env.filters['approx'] = approx
    env.filters['numspace'] = numspace
    env.filters['arabnum'] = arabnum

    corpus = []
    for x in args.corpus:
        with open (x) as fd:
            corpus.extend (filter (lambda x: x is not None, yaml.safe_load_all (fd)))
    layoutstats = {}
    for x in args.layoutstats:
        with open (x, 'rb') as fd:
            d = pickle.load (fd)
            layoutstats[d['layout']] = d

    corpustotal = {}
    for k in ('words', 'characters'):
        corpustotal[k] = sum (map (lambda x: x['stats'][k], corpus))

    tpl = env.get_template('index.html')

    tpl.stream (
            corpus=corpus,
            corpustotal=corpustotal,
            layoutstats=layoutstats,
            bokehres=bokehres,
            # XXX: not sure how to expose these properly to the template
            fingerOrder={LEFT: list (FingerType), RIGHT: list (reversed (FingerType))},
            Direction=Direction,
            ).dump (sys.stdout)

