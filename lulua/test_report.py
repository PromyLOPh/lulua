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

from decimal import Decimal

from .report import approx

def test_approx ():
    assert approx (0) == (Decimal ('0'), '')
    assert approx (0.01) == (Decimal ('0'), '')
    assert approx (0.05) == (Decimal ('0.1'), '')
    assert approx (1) == (Decimal ('1'), '')
    assert approx (100) == (Decimal ('100'), '')
    assert approx (999.9) == (Decimal ('999.9'), '')
    assert approx (999.91) == (Decimal ('999.9'), '')
    assert approx (999.99) == (Decimal ('1'), 'thousand')

    assert approx (10**3) == (Decimal ('1'), 'thousand')
    assert approx (10**6) == (Decimal ('1'), 'million')
    assert approx (10**9) == (Decimal ('1'), 'billion')
    assert approx (10**12) == (Decimal ('1000'), 'billion')

