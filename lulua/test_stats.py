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

from .stats import updateDictOp, approx

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

def test_approx ():
    assert approx (0) == (0, 0, '')
    assert approx (0.01) == (0, 0, '')
    assert approx (0.05) == (0, 1, '')
    assert approx (1) == (1, 0, '')
    assert approx (100) == (100, 0, '')
    assert approx (999.9) == (999, 9, '')

    assert approx (10**3) == (1, 0, 'thousand')
    assert approx (10**6) == (1, 0, 'million')
    assert approx (10**9) == (1, 0, 'billion')
    assert approx (10**12) == (1000, 0, 'billion')

