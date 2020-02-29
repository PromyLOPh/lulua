import sys, argparse, logging, pickle
from gettext import GNUTranslations, NullTranslations
from decimal import Decimal

import yaml
from jinja2 import Environment, PackageLoader
from bokeh.resources import CDN as bokehres

from .layout import LEFT, RIGHT, Direction, FingerType

def approx (i):
    """ Get approximate human-readable string for large number """

    units = ['', 'thousand', 'million', 'billion']
    base = Decimal (1000)
    i = Decimal (i)
    while round (i, 1) >= base and len (units) > 1:
        i /= base
        units.pop (0)
    return round (i, 1), units[0]

def numspace (s):
    """ Replace ordinary spaces with unicode FIGURE SPACE """
    return s.replace (' ', '\u2007')

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

