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

import operator
import pytest

from .stats import updateDictOp, SimpleStats, TriadStats, allStats
from .keyboard import defaultKeyboards
from .layout import defaultLayouts, ButtonCombination
from .writer import Writer, SkipEvent

def test_updateDictOp ():
    a = {1: 3}
    b = {1: 11, 7: 13}

    updateDictOp (a, b, operator.add)
    assert a == {1: 3+11, 7: 13}
    assert b == {1: 11, 7: 13}

    a = {'foo': {1: 3}}
    b = {'foo': {1: 7}}
    updateDictOp (a, b, operator.add)
    assert a == {'foo': {1: 3+7}}
    assert b == {'foo': {1: 7}}

@pytest.fixture
def writer ():
    """ Return a default, safe writer with known properties for a fixed layout """
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts['ar-lulua'].specialize (keyboard)
    return Writer (layout)
    
def test_simplestats (writer):
    keyboard = writer.layout.keyboard

    s = SimpleStats (writer)
    assert not s.unknown
    assert not s.combinations
    assert not s.buttons

    s.process (SkipEvent ('a'))
    assert len (s.unknown) == 1 and s.unknown['a'] == 1
    # no change for those
    assert not s.combinations
    assert not s.buttons

    dlcaps = keyboard['Dl_caps']
    bl1 = keyboard['Bl1']
    comb = ButtonCombination (frozenset ([dlcaps]), frozenset ([bl1]))
    s.process (comb)
    assert s.buttons[dlcaps] == 1
    assert s.buttons[bl1] == 1
    assert s.combinations[comb] == 1
    # no change
    assert len (s.unknown) == 1 and s.unknown['a'] == 1

    s2 = SimpleStats (writer)
    s2.update (s)
    assert s2 == s

def test_triadstats (writer):
    keyboard = writer.layout.keyboard

    s = TriadStats (writer)
    assert not s.triads

    s.process (SkipEvent ('a'))
    # should not change anything
    assert not s.triads

    dlcaps = keyboard['Dl_caps']
    bl1 = keyboard['Bl1']
    comb = ButtonCombination (frozenset ([dlcaps]), frozenset ([bl1]))
    for i in range (3):
        s.process (comb)
    assert len (s.triads) == 1 and s.triads[(comb, comb, comb)] == 1

    # sliding window -> increase
    s.process (comb)
    assert len (s.triads) == 1 and s.triads[(comb, comb, comb)] == 2

    # clear sliding window
    s.process (SkipEvent ('a'))
    assert len (s.triads) == 1 and s.triads[(comb, comb, comb)] == 2

    # thus no change here
    for i in range (2):
        s.process (comb)
    assert len (s.triads) == 1 and s.triads[(comb, comb, comb)] == 2

    # but here
    s.process (comb)
    assert len (s.triads) == 1 and s.triads[(comb, comb, comb)] == 3

def test_stats_process_value (writer):
    """ Make sure stats classes reject invalid values for .process() """

    for cls in allStats:
        s = cls (writer)
        with pytest.raises (ValueError):
            s.process (1)

        s.process (SkipEvent ('a'))
        s2 = cls (writer)
        s2.update (s)
        assert s2 == s
        assert not s2 == 1

