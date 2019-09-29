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

"""
Compute typing effort for triads according to
http://mkweb.bcgsc.ca/carpalx/?typing_effort

Extended by support for multiple layers/multiple key presses based on
suggestion by Martin Krzywinski. b_ix and p_ix with x in {1, 2, 3} are now a
sum of all key’s effort/penalty plus a multi-key penalty weighted by model
parameter k_s. Additionally the stroke path is evaluated for all triple
combinations (see code of _triadEffort).

Optimized for pypy, not cpython
"""

from collections import defaultdict, namedtuple
from itertools import chain, product
from typing import List, Tuple, Callable, Mapping, Dict

from .layout import LEFT, RIGHT, THUMB, INDEX, MIDDLE, RING, LITTLE, ButtonCombination
from .writer import Writer
from .util import first
from .keyboard import Button

ModelParams = namedtuple ('ModelParams', ['kBPS', 'k123S',
        'w0HRF', 'pHand', 'pRow', 'pFinger', 'fHRF', 'baselineEffort'])

models = dict (
# model parameters mod_01 from http://mkweb.bcgsc.ca/carpalx/?model_parameters
mod01 = ModelParams (
    # k_b, k_p, k_s
    kBPS = (0.3555, 0.6423, 0.4268),
    # k_1, k_2, k_3 plus extension k_S (weight for simultaneous key presses)
    k123S = (1.0, 0.367, 0.235, 1.0),
    # w0, wHand, wRow, wFinger
    w0HRF = (0.0, 1.0, 1.3088, 2.5948),
    pHand = {LEFT: 0.0, RIGHT: 0.0},
    # numbers, top, base, bottom, control (XXX not part of original model)
    pRow = (1.5, 0.5, 0.0, 1.0, 1.5),
    # symmetric penalties
    pFinger = {
        LEFT: {
            THUMB: 0.0, # XXX: not part of the original model
            INDEX: 0.0,
            MIDDLE: 0.0,
            RING: 0.5,
            LITTLE: 1.0,
            },
        RIGHT: {
            THUMB: 0.0, # XXX: not part of the original model
            INDEX: 0.0,
            MIDDLE: 0.0,
            RING: 0.5,
            LITTLE: 1.0,
            },
        },
    # fHand, fRow, fFinger
    fHRF = (1.0, 0.3, 0.3),
    # baseline key effort
    baselineEffort = {
        'Bl1': 5.0,
        'Bl2': 5.0,
        'Bl3': 4.0,
        'Bl4': 4.0,
        'Bl5': 4.0,
        'Bl6': 3.5,
        'Bl7': 4.5,
        'Br6': 4.0,
        'Br5': 4.0,
        'Br4': 4.0,
        'Br3': 4.0,
        'Br2': 4.0,
        'Br1': 4.5,

        'Cl1': 2.0,
        'Cl2': 2.0,
        'Cl3': 2.0,
        'Cl4': 2.0,
        'Cl5': 2.5,
        'Cr7': 3.0,
        'Cr6': 2.0,
        'Cr5': 2.0,
        'Cr4': 2.0,
        'Cr3': 2.5,
        'Cr2': 4.0,
        'Cr1': 6.0,

        'Dl_caps': 2.0, # XXX: dito
        'Dl1': 0.0,
        'Dl2': 0.0,
        'Dl3': 0.0,
        'Dl4': 0.0,
        'Dl5': 2.0,
        'Dr7': 2.0,
        'Dr6': 0.0,
        'Dr5': 0.0,
        'Dr4': 0.0,
        'Dr3': 0.0,
        'Dr2': 2.0,
        'Dr1': 4.0, # XXX: not in the original model

        'El_shift': 4.0,  # XXX: dito
        'El1': 4.0, # XXX: dito
        'El2': 2.0,
        'El3': 2.0,
        'El4': 2.0,
        'El5': 2.0,
        'El6': 3.5,
        'Er5': 2.0,
        'Er4': 2.0,
        'Er3': 2.0,
        'Er2': 2.0,
        'Er1': 2.0,
        'Er_shift': 4.0, # XXX: dito

        'Fr_altgr': 4.0, # XXX: dito
        },
    ),

# from paper “Ergonomic Keyboard Layout Designed for the Filipino Language”
salvo = ModelParams (
    # k_b, k_p, k_s
    # XXX: unchanged from original?
    kBPS = (0.3555, 0.6423, 0.4268),
    # k_1, k_2, k_3 plus extension k_S (weight for simultaneous key presses)
    # XXX: unchanged from original?
    k123S = (1.0, 0.367, 0.235, 1.0),
    # w0, wHand, wRow, wFinger
    # XXX: unchanged from original?
    w0HRF = (0.0, 1.0, 1.3088, 2.5948),
    pHand = {LEFT: 0.0, RIGHT: 0.0},
    # numbers, top, base, bottom, control (XXX not part of original model)
    # XXX: unchanged from original?
    pRow = (1.5, 0.5, 0.0, 1.0, 1.5),
    # symmetric penalties
    # normalized as suggested by https://normanlayout.info/about.html
    pFinger = {
        LEFT: {
            THUMB: 0.0, # XXX: not part of the original model
            INDEX: 1-(6.09/6.57),
            MIDDLE: 1-(5.65/6.57),
            RING: 1-(4.54/6.57),
            LITTLE: 1-(3.77/6.57),
            },
        RIGHT: {
            THUMB: 0.0, # XXX: not part of the original model
            INDEX: 1-(6.57/6.57),
            MIDDLE: 1-(6.37/6.57),
            RING: 1-(5.08/6.57),
            LITTLE: 1-(4.27/6.57),
            },
        },
    # fHand, fRow, fFinger
    fHRF = (1.0, 0.3, 0.3),
    # baseline key effort
    baselineEffort = {
        # XXX: from model 01, not part of the paper
        'Bl1': 5.0,
        'Bl2': 5.0,
        'Bl3': 4.0,
        'Bl4': 4.0,
        'Bl5': 4.0,
        'Bl6': 3.5,
        'Bl7': 4.5,
        'Br6': 4.0,
        'Br5': 4.0,
        'Br4': 4.0,
        'Br3': 4.0,
        'Br2': 4.0,
        'Br1': 4.5,

        'Cl1': 2.0,
        'Cl2': 2.0,
        'Cl3': 2.0,
        'Cl4': 2.0,
        'Cl5': 2.3,
        'Cr7': 3.0,
        'Cr6': 1.9,
        'Cr5': 2.0,
        'Cr4': 2.0,
        'Cr3': 2.2,
        'Cr2': 4.0, # XXX: dito
        'Cr1': 6.0,

        'Dl_caps': 2.0, # XXX: dito
        'Dl1': 0.0,
        'Dl2': 0.0,
        'Dl3': 0.0,
        'Dl4': 0.0,
        'Dl5': 1.8,
        'Dr7': 1.8,
        'Dr6': 0.0,
        'Dr5': 0.0,
        'Dr4': 0.0,
        'Dr3': 0.0,
        'Dr2': 2.0, # XXX: dito
        'Dr1': 4.0, # XXX: dito

        'El_shift': 4.0,  # XXX: dito
        'El1': 4.0, # XXX: dito
        'El2': 2.0,
        'El3': 2.0,
        'El4': 2.0,
        'El5': 2.0,
        'El6': 3.5,
        'Er5': 2.0,
        'Er4': 2.0,
        'Er3': 2.0,
        'Er2': 2.0,
        'Er1': 2.0,
        'Er_shift': 4.0, # XXX: dito

        'Fr_altgr': 4.0, # XXX: dito
        },
    ),
)

def madd (a, b):
    """ Given indexables a and b, computes a[0]*b[0]+a[1]*b[1]+… """
    s = 0
    for i in range (len (a)):
        s += a[i] * b[i]
    return s

class Carpalx:
    __slots__ = ('absEffort', 'N', 'params', '_cache', 'writer')

    def __init__ (self, params: ModelParams, writer: Writer):
        self.params = params
        self.writer = writer
        # reset should not reset the cache
        self._cache : Dict[Tuple[ButtonCombination], float] = dict ()
        self.reset ()

        # some runtime tests
        keyboard = writer.layout.keyboard
        assert keyboard.getRow (keyboard['Bl1']) == 0
        assert keyboard.getRow (keyboard['Cl1']) == 1
        assert keyboard.getRow (keyboard['Dl1']) == 2
        assert keyboard.getRow (keyboard['El1']) == 3

    def addTriad (self, triad : Tuple[ButtonCombination], n: float):
        self.absEffort += n*self._triadEffort (triad)
        self.N += n

    def removeTriad (self, triad: Tuple[ButtonCombination], n: float):
        self.absEffort -= n*self._triadEffort (triad)
        self.N -= n

    def addTriads (self, triads: Mapping[Tuple[ButtonCombination], float]) -> None:
        for t, n in triads.items ():
            self.addTriad (t, n)

    def reset (self) -> None:
        self.absEffort = 0.0
        self.N = 0.0

    def copy (self):
        """ Create a copy of this instance, sharing the cache """
        c = Carpalx (self.params, self.writer)
        c._cache = self._cache
        c.absEffort = self.absEffort
        c.N = self.N
        return c

    @property
    def effort (self) -> float:
        if self.N == 0:
            return 0
        else:
            return self.absEffort/self.N

    @staticmethod
    def _strokePathHand (hands) -> int:
        same = hands[0] == hands[1] and hands[1] == hands[2]
        alternating = hands[0] == hands[2] and hands[0] != hands[1]
        if alternating:
            return 1
        elif same:
            return 2
        else:
            # both hands, but not alternating
            return 0

    @staticmethod
    def _strokePathRow (rows: List[int]) -> int:
        # d will be positive for upward row changes and negative for downward
        d = (rows[0]-rows[1], rows[1]-rows[2], rows[0]-rows[2])
        #print ('rows', t, rows, d)
        if d[0] == 0 and d[1] == 0:
            # same row
            return 0
        elif (rows[0] == rows[1] and rows[2] > rows[1]) or (rows[1] > rows[0] and rows[1] == rows[2]):
            # downward progression, with repetition
            return 1
        elif (rows[0] == rows[1] and rows[2] < rows[1]) or (rows[1] < rows[0] and rows[1] == rows[2]):
            # upward progression, with repetition
            return 2
        elif max (map (abs, d)) <= 1:
            # some different, not monotonic, max row change 1
            return 3
        elif d[0] < 0 and d[1] < 0:
            # downward progression
            return 4
        elif d[0] > 0 and d[1] > 0:
            # upward progression
            # needs to be before 5
            return 6
        elif min (d[0], d[1]) < -1:
            # some different, not monotonic, max row change downward >1
            return 5
        elif max (d[0], d[1]) > 1:
            # some different, not monotonic, max row change upward >1
            return 7
        else:
            assert False, (rows, d)

    @staticmethod
    def _strokePathFinger (fingers, t) -> int:
        fingers = [int (f[1]) if f[0] == LEFT else 6+(5-f[1]) for f in fingers]
        same = fingers[0] == fingers[1] == fingers[2]
        allDifferent = fingers[0] != fingers[1] and fingers[1] != fingers[2] and fingers[0] != fingers[2]
        someDifferent = not same and not allDifferent
        if same:
            keyRepeat = t[0] == t[1] or t[1] == t[2] or t[0] == t[2]
            if keyRepeat:
                return 5
            else: # not keyRepeat
                return 7
        elif fingers[0] > fingers[2] > fingers[1] or fingers[0] < fingers[2] < fingers[1]:
            # rolling
            return 2
        elif allDifferent:
            monotonic = fingers[0] <= fingers[1] <= fingers[2] or fingers[0] >= fingers[1] >= fingers[2]
            if monotonic:
                return 0
            else:
                return 3
        elif someDifferent:
            monotonic = fingers[0] <= fingers[1] <= fingers[2] or fingers[0] >= fingers[1] >= fingers[2]
            if monotonic:
                keyRepeat = t[0] == t[1] or t[1] == t[2] or t[0] == t[2]
                if keyRepeat:
                    return 1
                else:
                    return 6
            else:
                return 4
        else:
            assert False

    def _strokePath (self, t: Tuple[Button, Button, Button]) -> Tuple[int, int, int]:
        """ Compute stroke path s for triad t """
        fingers = [self.writer.getHandFinger (x) for x in t]
        hands = [f[0] for f in fingers]
        keyboard = self.writer.layout.keyboard
        rows = [keyboard.getRow (key) for key in t]

        return self._strokePathHand (hands), self._strokePathRow (rows), self._strokePathFinger (fingers, t)

    def _penalty (self, key):
        hand, finger = self.writer.getHandFinger (key)
        keyboard = self.writer.layout.keyboard
        row = keyboard.getRow (key)
        params = self.params
        return madd (self.params.w0HRF, (1, params.pHand[hand], params.pRow[row], params.pFinger[hand][finger]))

    def _baseEffort (self, triad: Tuple[ButtonCombination], f: Callable[[Button], float]) -> float:
        """
        Compute b_i or p_i, depending on function f
        """

        k1, k2, k3, kS = self.params.k123S
        b = []
        for comb in triad:
            perButton = [f (btn) for btn in comb]
            numKeys = len (perButton)
            # extra effort for hitting multiple buttons, no extra effort for
            # just one button
            simultaneousPenalty = (numKeys-1)*kS
            b.append (sum (perButton) + simultaneousPenalty)
        return k1 * b[0] * (1 + k2 * b[1] * (1 + k3 * b[2]))

    def _triadEffort (self, triad: Tuple[ButtonCombination]) -> float:
        """ Compute effort for a single triad t, e_i """
        ret = self._cache.get (triad)
        if ret is not None:
            return ret
        #t = [first (x.buttons) for x in triad]
        params = self.params
        bmap = params.baselineEffort

        b = self._baseEffort (triad, lambda x: bmap[x.name])
        p = self._baseEffort (triad, self._penalty)

        # calculate stroke path for all possible triad combinations, i.e.
        # (Mod1-a, b, c) -> (Mod1, b, c), (a, b, c) and use the smallest
        # value. Suggested by Martin Krzywinski XXX: why?
        s = [madd (params.fHRF, self._strokePath (singleBtnTriad)) \
                for singleBtnTriad in product (*map (iter, triad))]
        s = min (s)

        ret = madd (params.kBPS, (b, p, s))
        self._cache[triad] = ret
        return ret

