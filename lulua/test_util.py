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

import pytest

from .util import displayText, limit, first

@pytest.mark.parametrize("s,expected", [
    ('foobar', False),
    # lonely shadda
    ('\u0651', True),
    # shadda+fatha
    ("\u0651\u064e", True),
    ('يّ', False),
    ])
def test_displayTextCombining (s, expected):
    assert displayText (s).startswith ('\u25cc') == expected

@pytest.mark.parametrize("l,n,expected", [
    ([], 1, []),
    (range (3), 0, []),
    (range (3), 3, list (range (3))),
    (range (1), 100, list (range (1))),
    (range (10000), 3, list (range (3))),
    ])
def test_limit (l, n, expected):
    assert list (limit (l, n)) == expected

def test_first ():
    assert first ([1, 2, 3]) == 1
    assert first (range (5)) == 0
    with pytest.raises (StopIteration):
        first ([])

