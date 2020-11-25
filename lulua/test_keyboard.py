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

import pytest

from .keyboard import defaultKeyboards, Button, dataDirectory
from .util import YamlLoader

def test_defaults ():
    k = defaultKeyboards['ibmpc105']
    assert k.name == 'ibmpc105'

    with pytest.raises (KeyError):
        k = defaultKeyboards['nonexistent']

    assert len (list (defaultKeyboards)) > 0

def test_keys_unique ():
    for kbd in defaultKeyboards:
        # both, ids and names must be unique
        havei = set ()
        havename = set ()
        for btn in kbd.keys ():
            assert btn.i not in havei
            havei.add (btn.i)

            assert btn.name not in havename
            havename.add (btn.name)

def test_keyboard_getRow ():
    k = defaultKeyboards['ibmpc105']
    for btn, expect in [(k['Bl1'], 0), (k['Cr1'], 1), (k['Dr1'], 2)]:
        assert k.getRow (btn) == expect
    
def test_keyboard_getattr ():
    k = defaultKeyboards['ibmpc105']
    assert k['Dr1'] == k.find ('Dr1')
    assert k['CD_ret'] == k.find ('CD_ret')
    assert k['Cr1'] != k.find ('El1')

    with pytest.raises (KeyError):
        k['nonexistent_button']

def test_button_uniqname ():
    a = Button ('a')
    assert a.name == 'a'

    b = Button ('b')
    assert b.name == 'b'

    assert a != b

    c = Button ('a')
    assert c.name == 'a'

    assert a == c
    assert b != c

    d = dict ()
    d[a] = 1
    assert a in d
    assert b not in d
    assert c in d
    d[b] = 2
    assert b in d

    # make sure we can only compare to Buttons
    assert a != 'hello'
    assert a != 1
    assert a != dict ()

def test_serialize ():
    """ Make sure serialize (deserialize (x)) of keyboards is identity """

    rawKeyboards = YamlLoader (dataDirectory, lambda x: x)
    name = 'ibmpc105'
    assert defaultKeyboards[name].serialize () == rawKeyboards[name]

