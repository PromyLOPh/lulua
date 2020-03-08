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

from io import StringIO

import pytest

from .writer import Writer, SkipEvent
from .layout import *
from .keyboard import defaultKeyboards

def toButtonComb (keyboard, data):
    lookupButton = lambda x: keyboard.find (x)
    return ButtonCombination (*map (lambda y: frozenset (lookupButton (z) for z in y), data))
    
def test_writer ():
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts['ar-linux'].specialize (keyboard)
    w = Writer (layout)

    f = w[LEFT][RING]
    assert f.number == RING
    assert f.hand.position == LEFT

typeData = [
    ('شسضص', [
        ('ش', (tuple (), ('Dl1', ))),
        ('س', (tuple (), ('Dl2', ))),
        ('ض', (tuple (), ('Cl1', ))),
        ('ص', (tuple (), ('Cl2', ))),
        ]),
    ('aصb', [
        (None, SkipEvent ('a')),
        ('ص', (tuple (), ('Cl2', ))),
        (None, SkipEvent ('b')),
        ]),
    ]

@pytest.mark.parametrize("s, expect", typeData)
def test_writer_type (s, expect):
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts['ar-linux'].specialize (keyboard)
    w = Writer (layout)

    data = StringIO (s)
    result = list (w.type (data))

    newExpect = []
    for char, comb in expect:
        if isinstance (comb, SkipEvent):
            newExpect.append ((char, comb))
        else:
            newExpect.append ((char, toButtonComb (keyboard, comb)))
    expect = newExpect
    assert result == expect

testCombs = [
    ([
        (('El_shift', ), ('Dr7', )),
        (('Er_shift', ), ('Dr7', )),
    ], 0, None
    ), ([
        (('El_shift', ), ('Dl5', )),
        (('Er_shift', ), ('Dl5', )),
    ], 1, None
    ), ([
        (tuple (), ('Fl_space', )),
        (tuple (), ('Fr_space', )),
    ], 0, (tuple (), ('Dr7', ))
    ), ([
        (tuple (), ('Fl_space', )),
        (tuple (), ('Fr_space', )),
    ], 1, (tuple (), ('Dl5', ))
    ), ([
        (tuple (), ('Fl_space', )),
        (tuple (), ('Fr_space', )),
    ], 1, (('El_shift', ), ('Dr7', ))
    ), ([
        (tuple (), ('Fl_space', )),
        (tuple (), ('Fr_space', )),
    ], 0, (('Er_shift', ), ('Dl5', ))
    ), ([
        # choose the shortest combination if there’s two available
        (tuple (), ('CD_ret', )),
        (('Er_shift', ), ('CD_ret', )),
        (('El_shift', ), ('CD_ret', )),
    ], 0, None),
    ([
        (('El_shift', ), ('Cl4', )),
        (('Er_shift', ), ('Cl4', )),
    ], 1, (tuple (), ('Fr_space', ))),
    ]

@pytest.mark.parametrize("combs, expect, prev", testCombs)
def test_writer_chooseComb (combs, expect, prev):
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts['ar-linux'].specialize (keyboard)
    w = Writer (layout)

    if prev:
        prev = toButtonComb (keyboard, prev)
        w.press (prev)
    combs = [toButtonComb (keyboard, x) for x in combs]
    result = w.chooseCombination (combs)
    assert result == combs[expect]

    if len (result) == 2:
        assert w.getHandFinger (first (result.modifier))[0] != w.getHandFinger (first (result.buttons))[0]
