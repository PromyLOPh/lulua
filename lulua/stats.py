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

import sys, operator, pickle, argparse, logging, yaml, math, time
from operator import itemgetter
from itertools import chain, groupby, product
from collections import defaultdict

from .layout import *
from .keyboard import defaultKeyboards
from .writer import SkipEvent, Writer
from .carpalx import Carpalx, models
from .plot import letterfreq, triadfreq
from .util import displayText

def updateDictOp (a, b, op):
    """ Update dict a by adding items from b using op """
    for k, v in b.items ():
        if k not in a:
            # simple
            a[k] = v
        else:
            if isinstance (v, dict):
                # recursive
                assert isinstance (a[k], dict)
                updateDictOp (a[k], v, op)
            elif isinstance (v, list):
                assert False
            else:
                a[k] = op (a[k], v)

class Stats:
    name = 'invalid'

    def process (self, event):
        raise NotImplementedError

    def update (self, other):
        raise NotImplementedError

class RunlenStats (Stats):
    __slots__ = ('lastHand', 'perHandRunlenDist', 'curPerHandRunlen',
            'fingerRunlen', 'lastFinger', 'fingerRunlenDist', 'writer')

    name = 'runlen'

    def __init__ (self, writer):
        self.writer = writer

        self.lastHand = None
        self.perHandRunlenDist = dict ((x, defaultdict (int)) for x in Direction)
        self.curPerHandRunlen = 0

        self.lastFinger = None
        self.fingerRunlenDist = dict (((x, y), defaultdict (int)) for x, y in product (iter (Direction), iter (FingerType)))
        self.fingerRunlen = 0

    def __eq__ (self, other):
        if not isinstance (other, RunlenStats):
            return NotImplemented
        return self.perHandRunlenDist == other.perHandRunlenDist
        
    def process (self, event):
        if isinstance (event, ButtonCombination):
            assert len (event.buttons) == 1
            thisHand, thisFinger = self.writer.getHandFinger (first (event.buttons))
            if self.lastHand and thisHand != self.lastHand:
                self.perHandRunlenDist[self.lastHand][self.curPerHandRunlen] += 1
                self.curPerHandRunlen = 0
            self.curPerHandRunlen += 1
            self.lastHand = thisHand

            fingerKey = (thisHand, thisFinger)
            if self.lastFinger and fingerKey != self.lastFinger:
                self.fingerRunlenDist[fingerKey][self.fingerRunlen] += 1
                self.fingerRunlen = 0
            self.fingerRunlen += 1
            self.lastFinger = fingerKey
        elif isinstance (event, SkipEvent):
            # reset state, we don’t know which button to press
            self.lastHand = None
            self.curPerHandRunlen = 0

            self.lastFinger = None
            self.fingerRunlen = 0
        else:
            raise ValueError ()

    def update (self, other):
        updateDictOp (self.perHandRunlenDist, other.perHandRunlenDist, operator.add)

class SimpleStats (Stats):
    __slots__ = ('buttons', 'combinations', 'unknown')

    name = 'simple'
    
    def __init__ (self, writer):
        # single buttons
        self.buttons = defaultdict (int)
        # button combinations
        self.combinations = defaultdict (int)
        self.unknown = defaultdict (int)

    def __eq__ (self, other):
        if not isinstance (other, SimpleStats):
            return NotImplemented
        return self.buttons == other.buttons and \
                self.combinations == other.combinations and \
                self.unknown == other.unknown

    def process (self, event):
        if isinstance (event, SkipEvent):
            self.unknown[event.char] += 1
        elif isinstance (event, ButtonCombination):
            for b in event:
                self.buttons[b] += 1
            self.combinations[event] += 1
        else:
            raise ValueError ()

    def update (self, other):
        updateDictOp (self.buttons, other.buttons, operator.add)
        updateDictOp (self.combinations, other.combinations, operator.add)
        updateDictOp (self.unknown, other.unknown, operator.add)

class TriadStats (Stats):
    """
    Button triad stats with an overlap of two.

    Whitespace buttons are ignored.
    """

    __slots__ = ('_triad', 'triads', '_writer', '_ignored')

    name = 'triads'

    def __init__ (self, writer):
        self._writer = writer

        self._triad = []
        self.triads = defaultdict (int)
        keyboard = self._writer.layout.keyboard
        self._ignored = frozenset (keyboard[x] for x in ('Fl_space', 'Fr_space', 'CD_ret', 'Cl_tab'))

    def __eq__ (self, other):
        if not isinstance (other, TriadStats):
            return NotImplemented
        return self.triads == other.triads

    def process (self, event):
        if isinstance (event, SkipEvent):
            # reset
            self._triad = []
        elif isinstance (event, ButtonCombination):
            assert len (event.buttons) == 1
            btn = first (event.buttons)
            if btn not in self._ignored:
                self._triad.append (event)

                if len (self._triad) > 3:
                    self._triad = self._triad[1:]
                    assert len (self._triad) == 3
                if len (self._triad) == 3:
                    k = tuple (self._triad)
                    self.triads[k] += 1
        else:
            raise ValueError ()

    def update (self, other):
        updateDictOp (self.triads, other.triads, operator.add)

class WordStats (Stats):
    """
    Word stats
    """

    __slots__ = ('words', '_currentWord', '_writer')

    name = 'words'

    def __init__ (self, writer):
        self._writer = writer

        self._currentWord = []
        self.words = defaultdict (int)

    def __eq__ (self, other):
        if not isinstance (other, WordStats):
            return NotImplemented
        return self.words == other.words

    def process (self, event):
        if isinstance (event, SkipEvent):
            # reset
            self._currentWord = []
        elif isinstance (event, ButtonCombination):
            text = self._writer.layout.getText (event)
            for t in text:
                cat = unicodedata.category (t)
                if cat in {'Lo', 'Mn'}:
                    # arabic letter or diacritic (non-spacing mark), everything
                    # else is considered a word-delimiter
                    self._currentWord.append (t)
                elif self._currentWord:
                    self.words[''.join (self._currentWord)] += 1
                    self._currentWord = []
        else:
            raise ValueError ()

    def update (self, other):
        updateDictOp (self.words, other.words, operator.add)

allStats = [SimpleStats, RunlenStats, TriadStats, WordStats]

def unpickleAll (fd):
    while True:
        try:
            yield pickle.load (fd)
        except EOFError:
            break

def makeCombined (keyboard):
    """ Create a dict which contains initialized stats, ready for combining (not actual writing!) """
    layout = defaultLayouts['null'].specialize (keyboard)
    w = Writer (layout)
    return dict ((cls.name, cls(w)) for cls in allStats)

def combine (args):
    keyboard = defaultKeyboards[args.keyboard]
    combined = makeCombined (keyboard)
    for r in unpickleAll (sys.stdin.buffer):
        for s in allStats:
            combined[s.name].update (r[s.name])
    pickle.dump (combined, sys.stdout.buffer, pickle.HIGHEST_PROTOCOL)

def pretty (args):
    stats = pickle.load (sys.stdin.buffer)

    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)
    writer = Writer (layout)

    buttonPresses = sum (stats['simple'].buttons.values ())
    print ('button presses', buttonPresses)
    for k, v in sorted (stats['simple'].buttons.items (), key=itemgetter (1)):
        print (f'{k} {v:10d} {v/buttonPresses*100:5.1f}%')

    combinationTotal = sum (stats['simple'].combinations.values ())
    items = stats['simple'].combinations.items ()
    n = len (items)
    print ('combinations', combinationTotal)
    for i, (k, v) in enumerate (sorted (items, key=itemgetter (1))):
        t = displayText (layout.getText (k))
        print (f'{n-i: 3d}. {t:4s} {k} {v:10d} {v/combinationTotal*100:7.3f}%')

    print ('unknown')
    for k, v in sorted (stats['simple'].unknown.items (), key=itemgetter (1)):
        print (f'{k!r} {v:10d}')

    combined = defaultdict (int)
    for hand, dist in stats['runlen'].perHandRunlenDist.items ():
        print (hand)
        total = sum (dist.values ())
        for k, v in sorted (dist.items (), key=itemgetter (0)):
            print (f'{k:2d} {v:10d} {v/total*100:5.1f}%')
            combined[k] += v
    print ('combined')
    total = sum (combined.values ())
    for k, v in combined.items ():
        print (f'{k:2d} {v:10d} {v/total*100:5.1f}%')

    print ('triads')
    for triad, count in sorted (stats['triads'].triads.items (), key=itemgetter (1)):
        print (f'{triad} {count:10d}')

    totalWords = sum (stats['words'].words.values ())
    print ('words', totalWords)
    for word, count in sorted (stats['words'].words.items (), key=itemgetter (1)):
        print (f'{word:20s} {count/totalWords*100:2.5f} {count:10d}')

    effort = Carpalx (models['mod01'], writer)
    effort.addTriads (stats['triads'].triads)
    print ('total effort (carpalx)', effort.effort)

def keyHeatmap (args):
    stats = pickle.load (sys.stdin.buffer)

    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)
    writer = Writer (layout)

    buttons = {}
    buttonPresses = sum (stats['simple'].buttons.values ())
    data = {'total': buttonPresses, 'buttons': buttons}
    for k, v in sorted (stats['simple'].buttons.items (), key=itemgetter (1)):
        assert k.name not in data
        buttons[k.name] = v
    yaml.dump (data, sys.stdout)

def layoutstats (args):
    stats = pickle.load (sys.stdin.buffer)

    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)
    writer = Writer (layout)

    hands = defaultdict (int)
    fingers = defaultdict (int)
    buttonPresses = sum (stats['simple'].buttons.values ())
    for btn, count in stats['simple'].buttons.items ():
        hand, finger = writer.getHandFinger (btn)
        hands[hand] += count
        fingers[(hand, finger)] += count

    asymmetry = hands[LEFT]/buttonPresses - hands[RIGHT]/buttonPresses
    pickle.dump (dict (
            layout=args.layout,
            hands=dict (hands),
            fingers=dict (fingers),
            buttonPresses=buttonPresses,
            asymmetry=asymmetry,
            ), sys.stdout.buffer)

def latinImeDict (args):
    """
    Create a dictionary for Android’s LatinIME input method from WordStats

    see https://android.googlesource.com/platform/packages/inputmethods/LatinIME/+/master/dictionaries/sample.combined
    """

    def f (p):
        """
        Word probability to logarithmic f-value.

        p = 1/(1.15^(255-f))
        """
        return 255+int (round (math.log (p, 1.15)))

    stats = pickle.load (sys.stdin.buffer)
    now = int (round (time.time ()))

    print ('# auto-generated by ' + __package__)
    print (f'dictionary=main:ar,locale=ar,description=Arabic wordlist,date={now},version=1')
    total = sum (stats['words'].words.values ())
    for word, count in sorted (stats['words'].words.items (), key=itemgetter (1), reverse=True):
        p = count/total
        print (f' word={word},f={f(p)}')

def corpusStats (args):
    """ Get corpus stats from stat files """
    stats = pickle.load (sys.stdin.buffer)
    meta = yaml.safe_load (args.metadata)

    meta['stats'] = dict (characters=sum (stats['simple'].combinations.values ()),
            words=sum (stats['words'].words.values ()))

    yaml.dump (meta, sys.stdout)
    # make document concatable
    print ('---')

def main ():
    parser = argparse.ArgumentParser(description='Process statistics files.')
    parser.add_argument('-l', '--layout', metavar='LAYOUT', help='Keyboard layout name')
    parser.add_argument('-k', '--keyboard', metavar='KEYBOARD',
            default='ibmpc105', help='Physical keyboard name')
    subparsers = parser.add_subparsers()
    sp = subparsers.add_parser('pretty')
    sp.set_defaults (func=pretty)
    sp = subparsers.add_parser('combine')
    sp.set_defaults (func=combine)
    sp = subparsers.add_parser('letterfreq')
    sp.set_defaults (func=letterfreq)
    sp = subparsers.add_parser('triadfreq')
    sp.add_argument('-c', '--cutoff', type=float, default=0.5, help='Only include the top x% of all triads')
    sp.add_argument('-r', '--reverse', action='store_true', help='Reverse sorting order')
    sp.add_argument('-s', '--sort', choices={'weight', 'effort', 'combined'}, default='weight', help='Sorter')
    sp.add_argument('-n', '--limit', type=int, default=0, help='Sorter')
    sp.set_defaults (func=triadfreq)
    sp = subparsers.add_parser('keyheatmap')
    sp.set_defaults (func=keyHeatmap)
    sp = subparsers.add_parser('layoutstats')
    sp.set_defaults (func=layoutstats)
    sp = subparsers.add_parser('latinime')
    sp.set_defaults (func=latinImeDict)
    sp = subparsers.add_parser('corpusstats')
    sp.add_argument('metadata', type=argparse.FileType ('r'))
    sp.set_defaults (func=corpusStats)

    logging.basicConfig (level=logging.INFO)
    args = parser.parse_args()

    return args.func (args)

