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
Misc utilities
"""

import os, yaml, pkg_resources, unicodedata

first = lambda x: next (iter (x))

def limit (l, n):
    """ Limit the number of items drawn from iterable l to n. """
    it = iter (l)
    for i in range (n):
        try:
            yield next (it)
        except StopIteration:
            break

class YamlLoader:
    """
    Simple YAML loader that searches the current path and the package’s
    resources (for defaults)
    """

    __slots__ = ('defaultDir', 'deserialize')

    def __init__ (self, defaultDir, deserialize):
        self.defaultDir = defaultDir
        self.deserialize = deserialize

    def __getitem__ (self, k, onlyRes=False):
        openfunc = []
        if not onlyRes:
            openfunc.append (lambda k: open (k, 'r'))
        # try with and without appending extension
        openfunc.append (lambda k: pkg_resources.resource_stream (__package__, os.path.join (self.defaultDir, k + '.yaml')))
        openfunc.append (lambda k: pkg_resources.resource_stream (__package__, os.path.join (self.defaultDir, k)))
        for f in openfunc:
            try:
                with f (k) as fd:
                    return self.deserialize (yaml.safe_load (fd))
            except FileNotFoundError:
                pass
            except yaml.reader.ReaderError:
                pass

        raise KeyError (k)

    def __iter__ (self):
        for res in pkg_resources.resource_listdir (__package__, self.defaultDir):
            # ignore dotfiles, only include yaml
            if not res.startswith ('.') and res.endswith ('.yaml'):
                yield self.__getitem__ (res, onlyRes=True)

def displayText (text):
    """ Convert text into a string that is always renderable without combining,
    control or invisible characters """
    if text is None:
        return text
    if all (map (lambda x: unicodedata.combining (x) != 0, text)):
        # add circle if combining
        return '\u25cc' + text
    invMap = {
        '\t': '⭾',
        '\n': '↳',
        ' ': '\u2423',
        '\b': '⌦',
        '\u200e': '[LRM]', # left to right mark
        '\u061c': '[ALM]', # arabic letter mark
        '\u202c': '[PDF]', # pop directional formatting
        "\u2066": '[LRI]', # left-to-right isolate (lri)
        "\u2067": '[RLI]', # right-to-left isolate (rli)
        "\u2069": '[PDI]', # pop directional isolate (pdi)
        }
    return invMap.get (text, text)
