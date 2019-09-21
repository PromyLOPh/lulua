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

import sys, operator, pickle, argparse, logging
from operator import itemgetter
from itertools import chain, groupby, product
from collections import defaultdict

from .layout import *
from .keyboard import defaultKeyboards
from .writer import SkipEvent, Writer
from .carpalx import Carpalx, model01 as cmodel01
from .plot import letterfreq, triadfreq

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

    def process (self, event):
        if isinstance (event, SkipEvent):
            self.unknown[event.char] += 1
        elif isinstance (event, ButtonCombination):
            for b in event:
                self.buttons[b] += 1
            self.combinations[event] += 1

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

    def update (self, other):
        updateDictOp (self.triads, other.triads, operator.add)

allStats = [SimpleStats, RunlenStats, TriadStats]

def unpickleAll (fd):
    while True:
        try:
            yield pickle.load (fd)
        except EOFError:
            break

def combine (args):
    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts['null'].specialize (keyboard)
    w = Writer (layout)
    combined = dict ((cls.name, cls(w)) for cls in allStats)
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
    for k, v in sorted (stats['simple'].buttons.items (), key=itemgetter (1)):
        print (f'{k} {v:10d} {v/buttonPresses*100:5.1f}%')
    print ('combinations')
    combinationTotal = sum (stats['simple'].combinations.values ())
    for k, v in sorted (stats['simple'].combinations.items (), key=itemgetter (1)):
        t = layout.getText (k)
        print (f'{t:4s} {k} {v:10d} {v/combinationTotal*100:5.1f}%')
    print ('unknown')
    for k, v in sorted (stats['simple'].unknown.items (), key=itemgetter (1)):
        print (f'{k!r} {v:10d}')

    #print ('fingers')
    #for k, v in sorted (stats['simple'].fingers.items (), key=itemgetter (0)):
    #    print (f'{k[0].name:5s} {k[1].name:6s} {v:10d} {v/buttonPresses*100:5.1f}%')

    #print ('hands')
    #for hand, fingers in groupby (sorted (stats['simple'].fingers.keys ()), key=itemgetter (0)):
    #    used = sum (map (lambda x: stats['simple'].fingers[x], fingers))
    #    print (f'{hand.name:5s} {used:10d} {used/buttonPresses*100:5.1f}%')

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

    for triad, count in sorted (stats['triads'].triads.items (), key=itemgetter (1)):
        print (f'{triad} {count:10d}')
    effort = Carpalx (cmodel01, writer)
    effort.addTriads (stats['triads'].triads)
    print ('total effort (carpalx)', effort.effort)

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
    sp.set_defaults (func=triadfreq)

    logging.basicConfig (level=logging.INFO)
    args = parser.parse_args()

    return args.func (args)

