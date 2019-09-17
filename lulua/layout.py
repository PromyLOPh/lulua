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

import sys, re, unicodedata, copy
from enum import IntEnum, unique
from collections import defaultdict, namedtuple
from itertools import chain
from typing import Text, FrozenSet, Iterator, List, Dict, Any, Tuple

from pygtrie import CharTrie
import pkg_resources
import yaml

from .util import first, YamlLoader

@unique
class Direction(IntEnum):
    LEFT = 1
    RIGHT = 2

# shortcut binds
LEFT = Direction.LEFT
RIGHT = Direction.RIGHT

@unique
class FingerType(IntEnum):
    LITTLE = 1
    RING = 2
    MIDDLE = 3
    INDEX = 4
    THUMB = 5

# shortcut binds
LITTLE = FingerType.LITTLE
RING = FingerType.RING
MIDDLE = FingerType.MIDDLE
INDEX = FingerType.INDEX
THUMB = FingerType.THUMB

class Hand:
    __slots__ = ('position', 'fingers')

    def __init__ (self, position, fingers=None):
        self.position = position
        self.fingers = []
        if fingers:
            for f in fingers:
                self.addFinger (f)

    def __repr__ (self):
        return f'Hand({self.position.name}, {self.fingers})'

    def __getitem__ (self, k):
        return next (filter (lambda x: x.number == k, self.fingers))

    def addFinger (self, f):
        self.fingers.append (f)
        f.hand = self

class Finger:
    __slots__ = ('number', 'hand')

    def __init__ (self, number):
        self.number = number
        self.hand = None

    def __repr__ (self):
        return f'Finger({self.number.name}) # {self.hand.position.name}'

from .keyboard import Button

class ButtonCombination:
    __slots__ = ('modifier', 'buttons', '_hash')

    def __init__ (self, modifier: FrozenSet[Button], buttons: FrozenSet[Button]):
        self.modifier = modifier
        self.buttons = buttons
        self._hash = hash ((self.modifier, self.buttons))

    def __len__ (self) -> int:
        return len (self.modifier) + len (self.buttons)

    def __iter__ (self) -> Iterator[Button]:
        return chain (self.modifier, self.buttons)

    def __repr__ (self):
        return f'ButtonCombination({self.modifier!r}, {self.buttons!r})'

    def __hash__ (self):
        return self._hash

    def __eq__ (self, other: Any) -> bool:
        if not isinstance (other, ButtonCombination):
            return NotImplemented
        return self.buttons == other.buttons and self.modifier == other.modifier

    def __getstate__ (self):
        return (self.modifier, self.buttons)

    def __setstate__ (self, state):
        self.__init__ (modifier=state[0], buttons=state[1])

Layer = namedtuple ('Layer', ['modifier', 'layout'])

from .keyboard import PhysicalKeyboard

class KeyboardLayout:
    """ Keyboard layout, i.e. physical button to character mapping """

    __slots__ = ('name', 'bufferLen', 't', 'layers', '_modifierToLayer', 'keyboard')

    def __init__ (self, name: Text, layers: List[Layer], keyboard: PhysicalKeyboard):
        # XXX: add sanity checks (i.e. modifier are not used elsewhere, no duplicates, …)
        self.name = name
        self.layers = layers
        self.keyboard = keyboard
        self._modifierToLayer : Dict[FrozenSet[Button], Tuple[int, Layer]] = dict ()
        self.bufferLen = 0
        t = self.t = CharTrie ()
        for i, l in enumerate (layers):
            for m in l.modifier:
                self._modifierToLayer[m] = (i, l)
            for button, v in l.layout.items ():
                if isinstance (v, str):
                    t.setdefault (v, [])
                    for m in l.modifier:
                        comb = ButtonCombination (m, frozenset ([button]))
                        t[v].append (comb)
                    self.bufferLen = max (len (v), self.bufferLen)

    def __call__ (self, buf: Text):
        """ Lookup a string and find the key used to type it """
        p = self.t.longest_prefix (buf)
        if p.key is None:
            raise KeyError ()
        return (p.key, p.value)

    def __iter__ (self):
        return iter (self.t.items ())

    def __eq__ (self, other):
        return self.layers == other.layers

    def __repr__ (self):
        return f'<KeyboardLayout {self.name}: {len (self.layers)} layers>'

    def copy (self):
        layers = copy.deepcopy (self.layers)
        return self.__class__ (self.name[:], layers)

    def getText (self, comb: ButtonCombination) -> Text:
        """ Get input text for combination """
        return self.modifierToLayer (comb.modifier)[1].layout[first (comb.buttons)]

    def getButtonText (self, button: Button) -> Iterator[Text]:
        """ Get text from all layers for a single button """
        for l in self.layers:
            yield l.layout.get (button, None)

    def modifierToLayer (self, mod: FrozenSet[Button]) -> Tuple[int, Layer]:
        """
        Look up (layer number, layer) for a given modifier combination mod
        """
        return self._modifierToLayer[mod]

    def isModifier (self, mod: FrozenSet[Button]) -> bool:
        """ Check if a given set of buttons is a modifier key """
        return mod in self._modifierToLayer

class GenericLayout:
    """ Layout for _any_ kind of keyboard, i.e. not specialized """

    __slots__ = ('name', 'layers')

    def __init__ (self, name: Text, layers: List):
        self.name = name
        self.layers = layers

    def __eq__ (self, other):
        return self.layers == other.layers

    def __len__ (self):
        return sum (len (layer.layout) for layer in self.layers)

    def buttons (self) -> Iterator[Tuple[Button, Text]]:
        """ Iterate over all layers and buttons """
        for l in self.layers:
            yield from l.layout.items ()

    @classmethod
    def deserialize (cls, data: Dict):
        layout = []
        layerSwitches = {}
        for layer in data['layout']:
            layout.append (Layer (modifier=[frozenset (x) for x in layer['modifier']], layout=layer['layer']))
        return cls (data['name'], layout)

    def serialize (self):
        def convertLayer (l):
            modifier = [list (x) for x in l.modifier]
            return dict (layer=l.layout, modifier=modifier)
        data = dict (name=self.name, layout=[convertLayer (x) for x in self.layers])
        return data

    def specialize (self, keyboard: PhysicalKeyboard) -> KeyboardLayout:
        """ Adapt this layout to an actual keyboard """
        def findButton (args):
            name, value = args
            return keyboard.find (name), value
        layers = []
        for l in self.layers:
            modifier = []
            for m in l.modifier:
                modifier.append (frozenset (keyboard.find (x) for x in m))
            layers.append (Layer (modifier=modifier, layout=dict (map (findButton, l.layout.items ()))))
        return KeyboardLayout (self.name, layers, keyboard=keyboard)

    @classmethod
    def fromKlc (cls, fd):
        """ Parse Microsoft Keyboard Layout Creator project file """
        def codeToText (c):
            # two symbols for NULL? Seriously Microsoft?
            if c == '%%':
                return None
            n = int (c, 16)
            if n == -1:
                return None
            return unicodedata.normalize ('NFD', chr (n))

        vkToButton = {
            'OEM_3': 'Bl2',
            '1': 'Bl2',
            '2': 'Bl3',
            '3': 'Bl4',
            '4': 'Bl5',
            '5': 'Bl6',
            '6': 'Bl7',
            '7': 'Br6',
            '8': 'Br5',
            '9': 'Br4',
            '0': 'Br3',
            'OEM_MINUS': 'Br2',
            'OEM_PLUS': 'Br1',

            'Q': 'Cl1',
            'W': 'Cl2',
            'E': 'Cl3',
            'R': 'Cl4',
            'T': 'Cl5',
            'Y': 'Cr7',
            'U': 'Cr6',
            'I': 'Cr5',
            'O': 'Cr4',
            'P': 'Cr3',
            'OEM_4': 'Cr2',
            'OEM_6': 'Cr1',
            'OEM_5': 'Cr0',

            'A': 'Dl1',
            'S': 'Dl2',
            'D': 'Dl3',
            'F': 'Dl4',
            'G': 'Dl5',
            'H': 'Dr7',
            'J': 'Dr6',
            'K': 'Dr5',
            'L': 'Dr4',
            'OEM_1': 'Dr3',
            'OEM_7': 'Dr2',
            #Dr1

            'OEM_102': 'El1',
            'Z': 'El2',
            'X': 'El3',
            'C': 'El4',
            'V': 'El5',
            'B': 'El6',
            'N': 'Er5',
            'M': 'Er4',
            'OEM_COMMA': 'Er3',
            'OEM_PERIOD': 'Er2',
            'OEM_2': 'Er1',

            'SPACE': 'Fl_space',
            }

        with fd:
            mode = None
            layers = [{} for i in range (6)]
            for line in fd:
                # strip comments
                try:
                    line = line[:line.index ('//')]
                    line = line[:line.index (';')]
                except ValueError:
                    pass
                line = line.strip ()
                if line.startswith ('LAYOUT'):
                    mode = 'layout'
                elif line == 'LIGATURE':
                    mode = None
                elif mode == 'layout':
                    try:
                        scancode, virtKey, cap, *code = re.split (r'\s+', line)
                    except ValueError:
                        continue
                    code = list (map (codeToText, code))
                    try:
                        button = vkToButton[virtKey]
                        for i, c in enumerate (code):
                            if c is not None:
                                layers[i][button] = c
                    except KeyError:
                        assert virtKey == 'DECIMAL'
                        pass

            layerSwitches = {
                0: [tuple ()],
                1: [('El_shift', ), ('Er_shift', )],
                2: [('Fl_ctrl', ), ('Fr_ctrl', )],
                3: [('El_shift', 'Fl_ctrl'), ('Er_shift', 'Fr_ctrl')],
                4: [('Er_altgr', )],
                5: [('El_shift', 'Er_altgr')],
                }
            return layers, layerSwitches

defaultLayouts = YamlLoader ('data/layouts', GenericLayout.deserialize)

def importKlc ():
    with open (sys.argv[1], 'r', encoding='utf16') as fd:
        layers, layerSwitches = Layout.fromKlc (fd)
        data = {'name': None, 'layout': [{'layer': l, 'modifier': [list (x) for x in layerSwitches[i]]} for i, l in enumerate (layers)]}
        yaml.dump (data, sys.stdout)

