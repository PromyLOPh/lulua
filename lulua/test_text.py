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

from .text import charMap, mapChars

def test_map_chars_mapped ():
    """ Make sure all chars in the map are mapped correctly """

    inText = ''
    expectText = ''
    for k, v in charMap.items ():
        inText += k
        expectText += v

    outText = mapChars (inText, charMap)
    assert outText == expectText

def test_map_chars_not_mapped ():
    """ No chars not in the map should be mapped """

    inText = ''
    expectText = ''
    for k, v in charMap.items ():
        inText += v
        expectText += v
    inText += 'a'
    expectText += 'a'

    outText = mapChars (inText, charMap)
    assert outText == expectText

