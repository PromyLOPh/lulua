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

import json
from operator import itemgetter
from typing import Text

from .layout import *

# XXX: dynamically index this by Button()?
defaultFingermap = {
    # fingers: hand (L/R), finger (counting from left to right on left hand and right to left on right hand)
    # B: number row
    # number keys left side
    'Bl1': (LEFT, LITTLE),
    'Bl2': (LEFT, LITTLE),
    'Bl3': (LEFT, LITTLE),
    'Bl4': (LEFT, RING),
    'Bl5': (LEFT, MIDDLE),
    'Bl6': (LEFT, INDEX),
    'Bl7': (LEFT, INDEX),
    # number keys right side
    'Br6': (RIGHT, INDEX),
    'Br5': (RIGHT, INDEX),
    'Br4': (RIGHT, MIDDLE),
    'Br3': (RIGHT, RING),
    'Br2': (RIGHT, LITTLE),
    'Br1': (RIGHT, LITTLE),
    'Br_bs': (RIGHT, LITTLE),
    # C: top row
    'Cl_tab': (LEFT, LITTLE),
    # letter keys left side
    'Cl1': (LEFT, LITTLE),
    'Cl2': (LEFT, RING),
    'Cl3': (LEFT, MIDDLE),
    'Cl4': (LEFT, INDEX),
    'Cl5': (LEFT, INDEX),
    # letter keys right side
    'Cr7': (RIGHT, INDEX),
    'Cr6': (RIGHT, INDEX),
    'Cr5': (RIGHT, MIDDLE),
    'Cr4': (RIGHT, RING),
    'Cr3': (RIGHT, LITTLE),
    'Cr2': (RIGHT, LITTLE),
    'Cr1': (RIGHT, LITTLE),
    # return key
    'CD_ret': (RIGHT, LITTLE),
    # D: middle row
    'Dl_caps': (LEFT, LITTLE),
    # letter keys left side
    'Dl1': (LEFT, LITTLE),
    'Dl2': (LEFT, RING),
    'Dl3': (LEFT, MIDDLE),
    'Dl4': (LEFT, INDEX),
    'Dl5': (LEFT, INDEX),
    # letter keys right side
    'Dr7': (RIGHT, INDEX),
    'Dr6': (RIGHT, INDEX),
    'Dr5': (RIGHT, MIDDLE),
    'Dr4': (RIGHT, RING),
    'Dr3': (RIGHT, LITTLE),
    'Dr2': (RIGHT, LITTLE),
    'Dr1': (RIGHT, LITTLE),
    # E: bottom row
    'El_shift': (LEFT, LITTLE),
    # letter keys left side
    'El1': (LEFT, LITTLE),
    'El2': (LEFT, LITTLE),
    'El3': (LEFT, RING),
    'El4': (LEFT, MIDDLE),
    'El5': (LEFT, INDEX),
    'El6': (LEFT, INDEX),
    # letter keys right side
    'Er5': (RIGHT, INDEX),
    'Er4': (RIGHT, INDEX),
    'Er3': (RIGHT, MIDDLE),
    'Er2': (RIGHT, RING),
    'Er1': (RIGHT, LITTLE),
    'Er_shift': (RIGHT, LITTLE),
    # F: bottom control row
    'Fl_ctrl': (LEFT, LITTLE),
    'Fl_fn': (LEFT, LITTLE),
    'Fl_win': (LEFT, THUMB),
    'Fl_alt': (LEFT, THUMB),
    'Fl_space': (LEFT, THUMB),
    'Fr_space': (RIGHT, THUMB),
    'Fr_altgr': (RIGHT, THUMB),
    'Fr_win': (RIGHT, THUMB),
    'Fr_menu': (RIGHT, THUMB),
    'Fr_ctrl': (RIGHT, LITTLE),
    }

class SkipEvent:
    __slots__ = ('char', )

    def __init__ (self, char: Text):
        assert len (char) == 1
        self.char = char

    def __eq__ (self, other):
        if not isinstance (other, SkipEvent):
            return NotImplemented
        return self.char == other.char

    def __repr__ (self):
        return f'SkipEvent({self.char!r})'

class Writer:
    """ The magical being whose commands the machine obeys """

    __slots__ = ('hands', 'lastCombination', 'layout')

    def __init__ (self, layout: KeyboardLayout):
        self.layout = layout
        # assuming 10 finger typing
        self.hands = {
                LEFT: Hand (LEFT, [Finger (x) for x in FingerType]),
                RIGHT: Hand (RIGHT, [Finger (x) for x in reversed (FingerType)]),
                }
        self.lastCombination = None

    def __getitem__ (self, k):
        return self.hands[k]

    def getHandFinger (self, button: Button):
        return defaultFingermap[button.name]

    def chooseCombination (self, combinations):
        """
        Choose the best button combination from the ones given.

        Return the actual button combination used.

        For instance:
        - A key on the right is usually combined with the shift button on the
          left and vice versa.
        - The spacebar is usually hit by the thumb of the previously unused
          hand. If two hands were used the one pressing the key (not the
          modifier) is chosen, since it’ll usually be closer.
        - The combination with the minimum amount of fingers required is chosen
          if multiple options are available
        """
        if len (combinations) == 1:
            return combinations[0]

        dirToScore = {LEFT: 1, RIGHT: -1}
        def calcEffort (comb):
            prev = self.lastCombination

            if prev is not None:
                prevBalance = 0
                for b in chain (prev.modifier or prev.buttons, comb.buttons):
                    pos = self.getHandFinger (b)[0]
                    prevBalance += dirToScore[pos]
            else:
                # prefer the left side (arbitrary decision)
                prevBalance = dirToScore[RIGHT]

            balance = 0
            for b in comb:
                pos = self.getHandFinger (b)[0]
                balance += dirToScore[pos]

            return (len (comb) << 16) | (abs (balance) << 8) | (abs (prevBalance) << 0)

        m = min (zip (map (calcEffort, combinations), combinations), key=itemgetter (0))
        return m[1]

    def press (self, comb):
        self.lastCombination = comb

    def type (self, fd):
        buf = ''
        while True:
            buf += fd.read (self.layout.bufferLen-len (buf))
            if not buf:
                break

            try:
                match, combinations = self.layout (buf)
                assert len (match) > 0, (match, combinations, buf)

                comb = self.chooseCombination (combinations)

                yield match, comb

                self.press (comb)
                buf = buf[len (match):]
            except KeyError:
                # ignore unknown characters
                yield None, SkipEvent (buf[0])
                buf = buf[1:]
                continue

