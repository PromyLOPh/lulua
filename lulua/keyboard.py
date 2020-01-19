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

# XXX move this to keyboard.yaml?
_buttonToXorgKeycode = {
    'Bl1': 49,
    'Bl2': 10,
    'Bl3': 11,
    'Bl4': 12,
    'Bl5': 13,
    'Bl6': 14,
    'Bl7': 15,
    'Br6': 16,
    'Br5': 17,
    'Br4': 18,
    'Br3': 19,
    'Br2': 20,
    'Br1': 21,
    'Br_bs': 22,
    'Cl_tab': 23,
    'Cl1': 24,
    'Cl2': 25,
    'Cl3': 26,
    'Cl4': 27,
    'Cl5': 28,
    'Cr7': 29,
    'Cr6': 30,
    'Cr5': 31,
    'Cr4': 32,
    'Cr3': 33,
    'Cr2': 34,
    'Cr1': 35,
    'CD_ret': 36,
    'Dl_caps': 66,
    'Dl1': 38,
    'Dl2': 39,
    'Dl3': 40,
    'Dl4': 41,
    'Dl5': 42,
    'Dr7': 43,
    'Dr6': 44,
    'Dr5': 45,
    'Dr4': 46,
    'Dr3': 47,
    'Dr2': 48,
    'Dr1': 51,
    'El_shift': 50,
    'El1': 94,
    'El2': 52,
    'El3': 53,
    'El4': 54,
    'El5': 55,
    'El6': 56,
    'Er5': 57,
    'Er4': 58,
    'Er3': 59,
    'Er2': 60,
    'Er1': 61,
    'Er_shift': 62,
    'Fl_ctrl': 37,
    'Fl_win': 133,
    'Fl_alt': 64,
    'Fl_space': 65,
    'Fr_space': 65,
    'Fr_altgr': 108,
    'Fr_win': 105,
    'Fr_menu': 135,
    'Fr_ctrl': 105,
    }

_buttonToKeyman = {
    'Bl1': 'K_BKSLASH',
    'Bl2': 'K_1',
    'Bl3': 'K_2',
    'Bl4': 'K_3',
    'Bl5': 'K_4',
    'Bl6': 'K_5',
    'Bl7': 'K_6',
    'Br6': 'K_7',
    'Br5': 'K_8',
    'Br4': 'K_9',
    'Br3': 'K_0',
    'Br2': 'K_LBRKT',
    'Br1': 'K_RBRKT',
    'Br_bs': 'K_BKSP',
    'Cl_tab': 'K_TAB',
    'Cl1': 'K_Q',
    'Cl2': 'K_W',
    'Cl3': 'K_E',
    'Cl4': 'K_R',
    'Cl5': 'K_T',
    'Cr7': 'K_Z',
    'Cr6': 'K_U',
    'Cr5': 'K_I',
    'Cr4': 'K_O',
    'Cr3': 'K_P',
    'Cr2': 'K_COLON',
    'Cr1': 'K_EQUAL',
    'CD_ret': 'K_ENTER',
    'Dl_caps': 'CAPS',
    'Dl1': 'K_A',
    'Dl2': 'K_S',
    'Dl3': 'K_D',
    'Dl4': 'K_F',
    'Dl5': 'K_G',
    'Dr7': 'K_H',
    'Dr6': 'K_J',
    'Dr5': 'K_K',
    'Dr4': 'K_L',
    'Dr3': 'K_BKQUOTE',
    'Dr2': 'K_QUOTE',
    'Dr1': 'K_SLASH',
    'El_shift': 'SHIFT', # XXX: there is no distinction between left/right
    'El1': 'K_oE2',
    'El2': 'K_Y',
    'El3': 'K_X',
    'El4': 'K_C',
    'El5': 'K_V',
    'El6': 'K_B',
    'Er5': 'K_N',
    'Er4': 'K_M',
    'Er3': 'K_COMMA',
    'Er2': 'K_PERIOD',
    'Er1': 'K_HYPHEN',
    'Er_shift': 'SHIFT',
    'Fl_ctrl': 'LCTRL',
    'Fl_win': 'K_?5B',
    'Fl_alt': 'LALT',
    'Fl_space': 'K_SPACE',
    'Fr_space': 'K_SPACE',
    'Fr_altgr': 'RALT',
    'Fr_win': 'K_?5C',
    'Fr_menu': 'K_?5D',
    'Fr_ctrl': 'RCTRL',
    }

# button to symbolic windows scancode usable in keyboard.c
# see windows header kbd.h (#define TXX _EQ(YY))
_buttonToWinScancode = {
    'Bl1': 'T29',
    'Bl2': 'T02',
    'Bl3': 'T03',
    'Bl4': 'T04',
    'Bl5': 'T05',
    'Bl6': 'T06',
    'Bl7': 'T07',
    'Br6': 'T08',
    'Br5': 'T09',
    'Br4': 'T0A',
    'Br3': 'T0B',
    'Br2': 'T0C',
    'Br1': 'T0D',
    'Br_bs': 'T0E',
    'Cl_tab': 'T0F',
    'Cl1': 'T10',
    'Cl2': 'T11',
    'Cl3': 'T12',
    'Cl4': 'T13',
    'Cl5': 'T14',
    'Cr7': 'T15',
    'Cr6': 'T16',
    'Cr5': 'T17',
    'Cr4': 'T18',
    'Cr3': 'T19',
    'Cr2': 'T1A',
    'Cr1': 'T1B',
    'CD_ret': 'T1C',
    'Dl_caps': 'T3A',
    'Dl1': 'T1E',
    'Dl2': 'T1F',
    'Dl3': 'T20',
    'Dl4': 'T21',
    'Dl5': 'T22',
    'Dr7': 'T23',
    'Dr6': 'T24',
    'Dr5': 'T25',
    'Dr4': 'T26',
    'Dr3': 'T27',
    'Dr2': 'T28',
    'Dr1': 'T2B',
    'El_shift': 'T2A',
    'El1': 'T56',
    'El2': 'T2C',
    'El3': 'T2D',
    'El4': 'T2E',
    'El5': 'T2F',
    'El6': 'T30',
    'Er5': 'T31',
    'Er4': 'T32',
    'Er3': 'T33',
    'Er2': 'T34',
    'Er1': 'T35',
    'Er_shift': 'T36',
    'Fl_ctrl': 'T1D',
    'Fl_win': 'X5B',
    'Fl_alt': 'T38',
    'Fl_space': 'T39',
    'Fr_space': 'T39',
    'Fr_altgr': 'X38',
    'Fr_win': 'X5C',
    'Fr_menu': 'X5D',
    'Fr_ctrl': 'X1D',
    }

class Button:
    __slots__ = ('width', 'isMarked', 'i')
    _idToName : Dict[int, Text] = {}
    _nameToId : Dict[Text, int] = {}
    _nextNameId = 0

    def __init__ (self, name: Text, width: float = 1, isMarked: bool = False):
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

    def __repr__ (self):
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

    @property
    def xorgKeycode (self):
        return _buttonToXorgKeycode[self.name]

    @property
    def keymanCode (self):
        return _buttonToKeyman[self.name]

    @property
    def windowsScancode (self):
        return _buttonToWinScancode[self.name]

    @classmethod
    def deserialize (self, data: Dict):
        kindMap = {'standard': Button, 'letter': LetterButton, 'multi': MultiRowButton}
        try:
            kind = data['kind']
            del data['kind']
        except KeyError:
            kind = 'standard'
        return kindMap[kind] (**data)

class LetterButton (Button):
    """
    A letter, number or symbol button, but not special keys like modifier, tab,
    …
    """
    def __init__ (self, name, isMarked=False):
        super().__init__ (name, width=1, isMarked=isMarked)

    def __repr__ (self):
        return f'LetterButton({self.name!r}, {self.isMarked})'

class MultiRowButton (Button):
    """
    A button spanning multiple rows, like the return button on european
    keyboards
    """

    __slots__ = ('span', )

    def __init__ (self, name, span, isMarked=False):
        super ().__init__ (name, width=1, isMarked=isMarked)
        self.span = span

    def __repr__ (self):
        return f'MultiRowButton({self.name!r}, {self.span!r}, {self.isMarked!r})'

class PhysicalKeyboard:
    __slots__ = ('name', 'rows', '_buttonToRow')

    def __init__ (self, name: Text, rows):
        self.name = name
        self.rows = rows

        self._buttonToRow = dict ()
        for i, (l, r) in enumerate (rows):
            for btn in chain (l, r):
                self._buttonToRow[btn] = i

    def __iter__ (self):
        return iter (self.rows)

    def __repr__ (self):
        return f'<PhysicalKeyboard {self.name} with {len (self)} keys>'

    def __len__ (self):
        return sum (map (lambda x: len(x[0])+len(x[1]), self))

    def __getitem__ (self, name: Text) -> Button:
        """ Find button by name """
        # XXX: speed up
        for k in self.keys ():
            if k.name == name:
                return k
        raise AttributeError (f'{name} is not a valid button name')

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
        return cls (data['name'], rows)

defaultKeyboards = YamlLoader ('data/keyboards', PhysicalKeyboard.deserialize)

