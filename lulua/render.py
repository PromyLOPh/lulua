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

import argparse, sys, logging
from collections import namedtuple, defaultdict
from operator import attrgetter
from datetime import datetime

import svgwrite
from svgwrite import em
import yaml

from .layout import LITTLE, RING, MIDDLE, INDEX, THUMB, GenericLayout, defaultLayouts
from .writer import Writer
from .keyboard import defaultKeyboards
from .util import first, displayText

RendererSettings = namedtuple ('RendererSetting', ['buttonMargin', 'middleGap', 'buttonWidth', 'rounded', 'shadowOffset'])

class Renderer:
    """ Keyboard to SVG renderer """

    __slots__ = ('keyboard', 'layout', 'settings', 'cursor', 'writer')

    defaultSettings = RendererSettings (
            buttonMargin=0.2,
            middleGap=0.1,
            buttonWidth=2,
            rounded=0.1,
            shadowOffset=0.05,
            )

    def __init__ (self, keyboard, layout=None, writer=None, settings=None):
        self.keyboard = keyboard
        self.layout = layout
        self.writer = writer
        self.settings = settings or self.defaultSettings

        self.cursor = [0, 0]

    def render (self):
        maxWidth = 0
        maxHeight = 0

        settings = self.settings
        self.cursor = [0, 0]

        # compute row widths so we can apply margin correction, balancing
        # out their widths
        rowWidth = []
        for l, r in self.keyboard:
            w = 0
            for btn in l:
                w += self.buttonWidth (btn) + settings.buttonMargin
            w += settings.middleGap
            for btn in r:
                w += self.buttonWidth (btn) + settings.buttonMargin
            w -= settings.buttonMargin
            rowWidth.append (w)
        logging.info (f'row width {rowWidth}')

        g = svgwrite.container.Group ()

        for l, r in self.keyboard:
            for btn in l:
                b, width = self._addButton (btn)
                g.add (b)
                self.cursor[0] += width + settings.buttonMargin
            self.cursor[0] += settings.middleGap
            for btn in r:
                b, width = self._addButton (btn)
                g.add (b)
                self.cursor[0] += width + settings.buttonMargin
            self.cursor[1] += settings.buttonWidth + settings.buttonMargin
            maxWidth = max (self.cursor[0], maxWidth)
            self.cursor[0] = 0
        maxHeight = self.cursor[1]

        return g, (maxWidth, maxHeight)

    def buttonWidth (self, btn):
        return btn.width * self.settings.buttonWidth

    def _addButton (self, btn):
        xoff, yoff = self.cursor
        settings = self.settings
        width = self.buttonWidth (btn)

        hand, finger = self.writer.getHandFinger (btn)

        gclass = ['button', f'finger-{finger.name.lower ()}', f'hand-{hand.name.lower ()}']

        g = svgwrite.container.Group ()

        # map modifier keys to arrows
        mod = frozenset ([btn])
        isModifier = self.layout.isModifier (mod)
        if isModifier:
            layerToArrow = {1: '⭡', 2: '⭧', 3: '⭨'}
            i, layer = self.layout.modifierToLayer (mod)
            buttonText = [layerToArrow[i]]
            gclass.append ('modifier')
        else:
            buttonText = list (map (displayText, self.layout.getButtonText (btn)))

        # background rect
        if any (buttonText):
            b = svgwrite.shapes.Rect (
                    insert=((xoff+settings.shadowOffset)*em, (yoff+settings.shadowOffset)*em),
                    size=(width*em, settings.buttonWidth*em),
                    rx=settings.rounded*em,
                    ry=settings.rounded*em,
                    class_='shadow')
            g.add (b)
        else:
            gclass.append ('unused')
        b = svgwrite.shapes.Rect (
                insert=(xoff*em, yoff*em),
                size=(width*em, settings.buttonWidth*em),
                rx=settings.rounded*em,
                ry=settings.rounded*em,
                class_='cap')
        g.add (b)

        g.attribs['class'] = ' '.join (gclass)

        # button marker
        if btn.isMarked:
            start = (xoff+width*0.3, yoff+settings.buttonWidth*0.9)
            end = (xoff+width*0.7, yoff+settings.buttonWidth*0.9)
            # its shadow
            l = svgwrite.shapes.Line (
                    map (lambda x: (x+settings.shadowOffset)*em, start),
                    map (lambda x: (x+settings.shadowOffset)*em, end),
                    stroke_width=0.07*em,
                    class_='marker-shadow')
            g.add (l)
            # the marker itself
            l = svgwrite.shapes.Line (
                    map (em, start),
                    map (em, end),
                    stroke_width=0.07*em,
                    class_='marker')
            g.add (l)

        # clock-wise from bottom-left to bottom-right
        textParam = [
            (-0.5, 0.6, 'layer-1'),
            (-0.5, -1/3, 'layer-2'),
            (0.5, -1/3, 'layer-3'),
            (0.5, 2/3, 'layer-4'),
            ]
        for text, (txoff, tyoff, style) in zip (buttonText, textParam):
            if text is None:
                continue
            # actual text must be inside tspan, so we can apply smaller font size
            # without affecting element position
            t = svgwrite.text.Text ('',
                    insert=((xoff+width/2+txoff)*em, (yoff+settings.buttonWidth/2+tyoff)*em),
                    text_anchor='middle',
                    class_='label')
            if text.startswith ('[') and text.endswith (']'):
                t.add (svgwrite.text.TSpan (text[1:-1],
                        class_='controlchar',
                        direction='ltr'))
                g.add (svgwrite.shapes.Rect (
                        insert=((xoff+width/2+txoff-0.4)*em, (yoff+settings.buttonWidth/2+tyoff-0.4)*em),
                        size=(0.8*em, 0.5*em),
                        stroke_width=0.05*em,
                        stroke_dasharray='5,3',
                        class_='controllabel'))
            else:
                t.add (svgwrite.text.TSpan (text, class_=style, direction='rtl'))
            g.add (t)

        return g, width

def unique (l, key):
    return dict ((key (v), v) for v in l).values ()

def renderSvg (args):
    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)
    writer = Writer (layout)

    style = """
            svg {
                font-family: "IBM Plex Arabic";
                font-size: 25pt;
            }
            .button.unused {
                opacity: 0.6;
            }
            .button .label .layer-1 {
            }
            .button.modifier .label .layer-1 {
                font-size: 80%;
            }
            .button .label .layer-2, .button .label .layer-3, .button .label .layer-4 {
                font-size: 80%;
                font-weight: 200;
            }
            .button .label .controlchar {
            font-size: 40%; font-family: sans-serif;
            }
            .button .cap {
                fill: #eee8d5;
            }
            .button.finger-little .shadow {
                fill: #dc322f; /* red */
            }
            .button.finger-ring .shadow {
                fill: #268bd2; /* blue */
            }
            .button.finger-middle .shadow {
                fill: #d33682; /* magenta */
            }
            .button.finger-index .shadow {
                fill: #6c71c4; /* violet */
            }
            .button.finger-thumb .shadow {
                fill: #2aa198; /* cyan */
            }
            .button .label {
                fill: #657b83;
            }
            .button .controllabel {
                stroke: #657b83;
                fill: none;
            }
            .button .marker-shadow {
                stroke: #93a1a1;
            }
            .button .marker {
                stroke: #fdf6e3;
            }
            """
    r = Renderer (keyboard, layout=layout, writer=writer)
    rendered, (w, h) = r.render ()
    d = svgwrite.Drawing(args.output, size=(w*em, h*em), profile='full')
    d.defs.add (d.style (style))
    d.add (rendered)
    d.save()

def renderXmodmap (args):
    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)

    with open (args.output, 'w') as fd:
        # inspired by https://neo-layout.org/neo_de.xmodmap
        fd.write ('\n'.join ([
            '!! auto-generated xmodmap',
            f'!! layout: {layout.name}',
            f'!! generated: {datetime.utcnow ()}',
            '',
            'clear Lock',
            'clear Mod2',
            'clear Mod3',
            'clear Mod5',
            '',
            ]))

        keycodeMap = defaultdict (list)
        # XXX: this is an ugly quirk to get layer 4 working
        # layers: 1, 2, 3, 5, 4, None, 6, 7
        for i in (0, 1, 2, 4, 3, 99999, 5, 6):
            if i >= len (layout.layers):
                for btn in unique (keyboard.keys (), key=attrgetter ('xorgKeycode')):
                    keycodeMap[btn].append ('NoSymbol')
                continue
            l = layout.layers[i]
            # space button shares the same keycode and must be removed
            for btn in unique (keyboard.keys (), key=attrgetter ('xorgKeycode')):
                if not layout.isModifier (frozenset ([btn])):
                    text = l.layout.get (btn)
                    if not text:
                        if btn.name == 'Br_bs' and i == 0:
                            text = 'BackSpace'
                        else:
                            text = 'NoSymbol'
                    else:
                        # some keys cannot be represented by unicode
                        # characters and must be mapped
                        specialMap = {
                            '\t': 'Tab',
                            '\n': 'Return',
                            ' ': 'space',
                            }
                        text = specialMap.get (text, f'U{ord (text):04X}')
                    keycodeMap[btn].append (text)
        # XXX layer modmap functionality is fixed for now
        layerMap = [
            [],
            ['Shift_L', 'Shift_Lock'],
            ['ISO_Group_Shift', 'ISO_Group_Shift', 'ISO_First_Group', 'NoSymbol'],
            ['ISO_Level3_Shift', 'ISO_Level3_Shift', 'ISO_Group_Shift', 'ISO_Group_Shift', 'ISO_Level3_Lock', 'NoSymbol'],
            ]
        for i, l in enumerate (layout.layers):
            for m in l.modifier:
                assert len (m) <= 1, ('multi-key modifier not supported', m)
                if not m:
                    continue
                btn = first (m)
                keycodeMap[btn] = layerMap[i]

        for btn, v in keycodeMap.items ():
            v = '\t'.join (v)
            fd.write (f'!! {btn.name}\nkeycode {btn.xorgKeycode} = {v}\n')
        fd.write ('\n'.join (['add Mod3 = ISO_First_Group', 'add Mod5 = ISO_Level3_Shift', '']))

def renderKeyman (args):
    """ Rudimentary keyman script generation. Note that keyman is somewhat
    unflexible when it comes to shift states and therefore layouts with
    non-standard shift keys/states won’t work. """

    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)

    with open (args.output, 'w') as fd:
        fd.write ('\n'.join ([
            'c Auto-generated file for Keyman 11.0',
            f'c layout: {layout.name}',
            f'c generated: {datetime.utcnow ()}',
            '',
            'store(&version) "9.0"',
            f'store(&name)    "{layout.name}"',
            'store(&mnemoniclayout) "0"',
            'store(&targets) "any"',
            '',
            'begin Unicode > use(main)',
            'group(main) using keys',
            '',
            ]))
        for i, l in enumerate (layout.layers):
            for m in l.modifier:
                for x in m:
                    if x.keymanCode.startswith ('K_') or x.keymanCode == 'CAPS':
                        logging.error (f'Keyman does not support custom modifier like {m}. Your layout will not work correctly.')
                        break
                for btn, text in l.layout.items ():
                    comb = ' '.join ([x.keymanCode for x in m] + [btn.keymanCode])
                    text = ' '.join ([f'U+{ord (x):04X}' for x in text])
                    fd.write (f'+ [{comb}] > {text}\n')

def render ():
    parser = argparse.ArgumentParser(description='Render keyboard into output format.')
    parser.add_argument('-l', '--layout', metavar='LAYOUT', help='Keyboard layout name')
    parser.add_argument('-k', '--keyboard', metavar='KEYBOARD',
            default='ibmpc105', help='Physical keyboard name')
    subparsers = parser.add_subparsers()
    sp = subparsers.add_parser('svg')
    sp.set_defaults (func=renderSvg)
    sp = subparsers.add_parser('xmodmap')
    sp.set_defaults (func=renderXmodmap)
    sp = subparsers.add_parser('keyman')
    sp.set_defaults (func=renderKeyman)
    parser.add_argument('output', metavar='FILE', help='Output file')

    logging.basicConfig (level=logging.INFO)
    args = parser.parse_args()

    return args.func (args)

