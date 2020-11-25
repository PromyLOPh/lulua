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

import pkg_resources
from itertools import chain
from typing import Text, Dict, Iterator, List

from .util import YamlLoader

class Button:
    """ A single physical button on the keyboard """

    __slots__ = ('width', 'isMarked', 'i', 'scancode')
    _idToName : Dict[int, Text] = {}
    _nameToId : Dict[Text, int] = {}
    _nextNameId = 0
    serializedName = 'standard'

    def __init__ (self, name: Text, width: float = 1, isMarked: bool = False, scancode = None):
        # map names to integers for fast comparison/hashing
        i = Button._nameToId.get (name)
        if i is None:
            i = Button._nextNameId
            Button._nextNameId += 1
            Button._idToName[i] = name
            Button._nameToId[name] = i
        self.i = i
        self.width = width
        # marked with an haptic line, for better orientation
        self.isMarked = isMarked
        # scancode map, although they are not all technically scancodes, they
        # are some low-level representation of the physical key
        self.scancode = scancode
        # special case for windows
        if self.scancode and 'windows' in self.scancode:
            self.scancode['windows'] = tuple (self.scancode['windows'])

    def __repr__ (self): # pragma: no cover
        return f'Button({self.name!r}, {self.width}, {self.isMarked})'

    def __eq__ (self, other):
        if not isinstance (other, Button):
            return NotImplemented
        return self.i == other.i

    def __hash__ (self):
        return hash (self.i)

    @property
    def name (self):
        return Button._idToName[self.i]

    @classmethod
    def deserialize (self, data: Dict):
        kindMap = dict (map (lambda x: (x.serializedName, x),
                (Button, LetterButton, MultiRowButton)))
        try:
            kind = data['kind']
            del data['kind']
        except KeyError:
            kind = 'standard'
        return kindMap[kind] (**data)

    def serialize (self):
        d = dict (name=self.name, width=self.width, scancode=self.scancode)
        if self.__class__ is not Button:
            d['kind'] = self.serializedName
        if self.isMarked:
            d['isMarked'] = self.isMarked
        # turn the tuple back into a list
        if d['scancode'] and 'windows' in d['scancode']:
            d['scancode']['windows'] = list (d['scancode']['windows'])
        return d

class LetterButton (Button):
    """
    A letter, number or symbol button, but not special keys like modifier, tab,
    …
    """
    serializedName = 'letter'

    def __init__ (self, name, width=1, isMarked=False, scancode=None):
        super().__init__ (name, width=width, isMarked=isMarked, scancode=scancode)

    def __repr__ (self): # pragma: no cover
        return f'LetterButton({self.name!r}, {self.isMarked})'

class MultiRowButton (Button):
    """
    A button spanning multiple rows, like the return button on european
    keyboards
    """

    __slots__ = ('span', )
    serializedName = 'multi'

    def __init__ (self, name, span, width=1, isMarked=False, scancode=None):
        super ().__init__ (name, width=width, isMarked=isMarked, scancode=scancode)
        self.span = span

    def __repr__ (self): # pragma: no cover
        return f'MultiRowButton({self.name!r}, {self.span!r}, {self.isMarked!r})'

    def serialize (self):
        d = super ().serialize ()
        d['span'] = self.span
        return d

class PhysicalKeyboard:
    __slots__ = ('name', 'description', 'rows', '_buttonToRow')

    def __init__ (self, name: Text, description: Text, rows):
        self.name = name
        self.description = description
        self.rows = rows

        self._buttonToRow = dict ()
        for i, (l, r) in enumerate (rows):
            for btn in chain (l, r):
                self._buttonToRow[btn] = i

    def __iter__ (self):
        return iter (self.rows)

    def __repr__ (self): # pragma: no cover
        return f'<PhysicalKeyboard {self.name} with {len (self)} keys>'

    def __len__ (self):
        return sum (map (lambda x: len(x[0])+len(x[1]), self))

    def __getitem__ (self, name: Text) -> Button:
        """ Find button by name """
        # XXX: speed up
        for k in self.keys ():
            if k.name == name:
                return k
        raise KeyError (f'{name} is not a valid button name')

    def keys (self) -> Iterator[Button]:
        """ Iterate over all keys """
        for row in self.rows:
            yield from chain.from_iterable (row)

    def find (self, name: Text) -> Button:
        return self[name]

    def getRow (self, btn: Button):
        return self._buttonToRow[btn]

    @classmethod
    def deserialize (cls, data: Dict):
        rows = []
        for l, r in data['rows']:
            row : List[List[Button]] = [[], []]
            for btn in l:
                row[0].append (Button.deserialize (btn))
            for btn in r:
                row[1].append (Button.deserialize (btn))
            rows.append (row)
        return cls (data['name'], data['description'], rows)

    def serialize (self):
        rows = []
        for l, r in self.rows:
            newRow = [[], []]
            for btn in l:
                newRow[0].append (btn.serialize ())
            for btn in r:
                newRow[1].append (btn.serialize ())
            rows.append (newRow)
        return dict (name=self.name, description=self.description, rows=rows)

dataDirectory = 'data/keyboards'
defaultKeyboards = YamlLoader (dataDirectory, PhysicalKeyboard.deserialize)

