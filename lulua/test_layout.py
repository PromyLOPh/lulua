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

import unicodedata
from itertools import product

import pytest

from .layout import defaultLayouts, GenericLayout, ButtonCombination
from .keyboard import defaultKeyboards, LetterButton

@pytest.mark.parametrize("layout", defaultLayouts, ids=[l.name for l in defaultLayouts])
def test_atomic (layout):
    """ Make sure layout text strings are atomic (i.e. not decomposeable) and not empty """
    for btn, text in layout.buttons ():
        assert isinstance (text, str)
        assert text != '', (btn, )
        for char in text:
            d = unicodedata.decomposition (char)
            # allow compat decompositions like … -> ...
            if d.split (' ', 1)[0] not in {'<compat>', '<isolated>', '<medial>', '<initial>', '<noBreak>'}:
                assert d == '', (char, btn)

@pytest.mark.parametrize("layout", defaultLayouts, ids=[l.name for l in defaultLayouts])
def test_genericlayout_len (layout):
    assert len (layout) == len (list (layout.buttons ()))

@pytest.mark.parametrize("layout", defaultLayouts, ids=[l.name for l in defaultLayouts])
def test_layout_serialize (layout):
    assert GenericLayout.deserialize (layout.serialize ()) == layout

@pytest.mark.parametrize("a, b", product (defaultLayouts, defaultLayouts))
def test_layout_equality (a, b):
    if a.name == b.name:
        # this is true for our default layouts only
        assert a == b
    else:
        assert a != b

@pytest.mark.parametrize("layout", defaultLayouts, ids=[l.name for l in defaultLayouts])
def test_layout_text_identity (layout):
    """ Make sure __call__ and getText work for every layout """
    keyboard = defaultKeyboards['ibmpc105']
    layout = layout.specialize (keyboard)

    for match, combinations in layout:
        # all combinations produce this match
        for comb in combinations:
            assert layout.getText (comb) == match
        # this match produces all combinations
        newmatch, newcombinations = layout (match)
        assert newmatch == match
        assert set (newcombinations) == set (combinations)

def test_layout_isModifier ():
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts['ar-linux'].specialize (keyboard)
    assert layout.isModifier (frozenset ([keyboard['El_shift']]))
    assert layout.isModifier (frozenset ([keyboard['Er_shift']]))
    assert not layout.isModifier (frozenset ([keyboard['Dr1']]))

def test_buttoncomb_eq ():
    a = ButtonCombination (frozenset (['a']), frozenset (['b']))
    b = ButtonCombination (frozenset (['a']), frozenset (['b']))
    c = ButtonCombination (frozenset (['a']), frozenset (['c']))

    assert a == b
    assert a != c and b != c

    d = dict ()
    d[a] = 'a'
    assert b in d
    assert c not in d

