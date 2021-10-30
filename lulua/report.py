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

import sys, argparse, logging, pickle, math, unicodedata
from gettext import GNUTranslations, NullTranslations
from decimal import Decimal
from fractions import Fraction

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

def fraction (n, maxdenom=10):
    """ Turn floating number n into a human-digestable fraction """
    f = Fraction (n).limit_denominator (maxdenom)
    return f'{f.numerator}\u2044{f.denominator}'

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
    env.filters['fraction'] = fraction

    # Map global variables to Arabic letter romanizations, so we can use
    # them easily in text.
    # Taken from Abu-Chacra’s Arabic – An Essential Grammar. It’s
    # too difficult for now to write a general-purpose romanization
    # function, because it would need a dictionary.
    letterNames = {
        'Hamzah': ('Hamzah', 'ء'),
        'Alif': ('ᵓAlif', 'ا'),
        'Alifhamzah': ('ᵓAlif-hamzah', 'أ'),
        'Wawhamzah': ('Wa\u0304w-hamzah', 'ؤ'),
        'Yahamzah': ('Ya\u0304ᵓ-hamzah', 'ئ'),
        'Ba': ('Baᵓ', 'ب'),
        'Ta': ('Taᵓ', 'ت'),
        'Tha': ('T\u0331aᵓ', 'ث'),
        'Ra': ('Raᵓ', 'ر'),
        'Dal': ('Da\u0304l', 'د'),
        'Dhal': ('D\u0331a\u0304l', 'ذ'),
        'Qaf': ('Qa\u0304f', 'ق'),
        'Lam': ('La\u0304m', 'ل'),
        'Lamalif': ('La\u0304m-ᵓalif', 'لا'),
        'Mim': ('Mi\u0304m', 'م'),
        'Nun': ('Nu\u0304n', 'ن'),
        'Waw': ('Wa\u0304w', 'و'),
        'Ya': ('Ya\u0304ᵓ', 'ي'),
        'Tamarbutah': ('Ta\u0304ᵓ marbu\u0304t\u0323ah', 'ة'),
        'Alifmaqsurah': ('ᵓAlif maqs\u0323u\u0304rah', 'ى'),
        }
    for k, (romanized, arabic) in letterNames.items ():
        env.globals[k] = f'{romanized} <bdo lang="ar">({arabic})</bdo>'
        env.globals[k.lower ()] = env.globals[k].lower ()
        env.globals[k + '_'] = romanized
        env.globals[k.lower () + '_'] = romanized.lower ()

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

