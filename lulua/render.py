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

import argparse, sys, logging, pkg_resources, base64, unicodedata
from collections import namedtuple, defaultdict
from itertools import chain
from operator import attrgetter
from datetime import datetime
from xml.etree import ElementTree

import svgwrite
import yaml

from .layout import LITTLE, RING, MIDDLE, INDEX, THUMB, GenericLayout, defaultLayouts
from .writer import Writer
from .keyboard import defaultKeyboards, LetterButton
from .util import first, displayText

RendererSettings = namedtuple ('RendererSetting', ['buttonMargin', 'middleGap', 'buttonWidth', 'rounded', 'shadowOffset', 'markerStroke'])

class Renderer:
    """ Keyboard to SVG renderer """

    __slots__ = ('keyboard', 'layout', 'settings', 'cursor', 'writer', 'keyHighlight')

    defaultSettings = RendererSettings (
            buttonMargin=20,
            middleGap=10,
            buttonWidth=200,
            rounded=10,
            shadowOffset=5,
            markerStroke=7,
            )

    def __init__ (self, keyboard, layout=None, writer=None, settings=None, keyHighlight=None):
        self.keyboard = keyboard
        self.layout = layout
        self.writer = writer
        self.settings = settings or self.defaultSettings
        self.keyHighlight = keyHighlight or {}

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

        # background rect if any text
        if any (buttonText):
            b = svgwrite.shapes.Rect (
                    insert=((xoff+settings.shadowOffset), (yoff+settings.shadowOffset)),
                    size=(width, settings.buttonWidth),
                    rx=settings.rounded,
                    ry=settings.rounded,
                    class_='cap shadow')
            g.add (b)
        else:
            gclass.append ('unused')
        # main key rect
        b = svgwrite.shapes.Rect (
                insert=(xoff, yoff),
                size=(width, settings.buttonWidth),
                rx=settings.rounded,
                ry=settings.rounded,
                class_='cap')
        g.add (b)

        g.attribs['class'] = ' '.join (gclass)

        # button marker
        if btn.isMarked:
            start = (xoff+width*0.3, yoff+settings.buttonWidth*0.9)
            end = (xoff+width*0.7, yoff+settings.buttonWidth*0.9)
            # its shadow
            l = svgwrite.shapes.Line (
                    map (lambda x: (x+settings.shadowOffset), start),
                    map (lambda x: (x+settings.shadowOffset), end),
                    stroke_width=settings.markerStroke,
                    class_='marker shadow')
            g.add (l)
            # the marker itself
            l = svgwrite.shapes.Line (
                    start,
                    end,
                    stroke_width=settings.markerStroke,
                    class_='marker')
            g.add (l)

        # highlight rect
        highlight = self.keyHighlight.get (btn.name, 0)
        b = svgwrite.shapes.Rect (
                insert=(xoff, yoff),
                size=(width, settings.buttonWidth),
                rx=settings.rounded,
                ry=settings.rounded,
                class_='cap highlight',
                style=f'opacity: {highlight}')
        g.add (b)

        # clock-wise from bottom-left to bottom-right, offsets are relative to buttonWidth and button center
        textParam = [
            (-0.25, 0.3, 'layer-1'),
            (-0.25, -0.15, 'layer-2'),
            (0.25, -0.15, 'layer-3'),
            (0.25, 0.3, 'layer-4'),
            ]
        # XXX: could probably def/use these
        for extraclass, morexoff, moreyoff in [(['shadow'], settings.shadowOffset, settings.shadowOffset), ([], 0, 0)]:
            class_ = ['label'] + extraclass
            controlclass_ = ['controllabel'] + extraclass
            for text, (txoff, tyoff, style) in zip (buttonText, textParam):
                if text is None:
                    continue
                txoff = txoff*settings.buttonWidth + morexoff
                tyoff = tyoff*settings.buttonWidth + moreyoff
                # actual text must be inside tspan, so we can apply smaller font size
                # without affecting element position
                t = svgwrite.text.Text ('',
                        insert=((xoff+width/2+txoff), (yoff+settings.buttonWidth/2+tyoff)),
                        text_anchor='middle',
                        class_=' '.join (class_))
                if text.startswith ('[') and text.endswith (']'):
                    # XXX: should find us a font which has glyphs for control chars
                    t.add (svgwrite.text.TSpan (text[1:-1],
                            class_='controlchar',
                            direction='ltr'))
                    g.add (svgwrite.shapes.Rect (
                            insert=((xoff+width/2+txoff-40), (yoff+settings.buttonWidth/2+tyoff-40)),
                            size=(80, 50),
                            stroke_width=2,
                            stroke_dasharray='15,8',
                            class_=' '.join (controlclass_)))
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

    keyHeat = {}
    if args.heatmap:
        maxHeat = max (args.heatmap['buttons'].values ())
        keyHeat = dict ((k, v/maxHeat) for k, v in args.heatmap['buttons'].items ())

    r = Renderer (keyboard, layout=layout, writer=writer, keyHighlight=keyHeat)
    rendered, (w, h) = r.render ()
    d = svgwrite.Drawing(args.output, size=(w, h), profile='full')

    # using fonts via url() only works in stand-alone documents, not when
    # embedding into a website
    # see https://github.com/mozman/svgwrite/blob/master/examples/using_fonts.py#L36
    # which we cannot use since it does not support font-weight
    style = ''
    fonts = [
            ('IBM Plex Arabic', 100, '3rdparty/plex/IBM-Plex-Arabic/fonts/complete/woff2/IBMPlexArabic-Thin.woff2'),
            ('IBM Plex Arabic', 400, '3rdparty/plex/IBM-Plex-Arabic/fonts/complete/woff2/IBMPlexArabic-Regular.woff2')
            ]
    for font, weight, path in fonts:
        with open (path, 'rb') as fd:
            data = base64.b64encode (fd.read ()).decode ('utf-8')
        style += f"""
                @font-face {{
                font-family: '{font}';
                font-style: normal;
                font-weight: {weight};
                src: url("data:application/font-woff2;charset=utf-8;base64,{data}") format('woff2');
                }}
                """

    style += args.style.read ().decode ('utf-8')
    d.defs.add (d.style (style))

    d.add (rendered)
    d.save (pretty=True)

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

def renderAsk (args):
    """
    Render keyboard to Anysoft Keyboard XML layout file

    Can be packaged/used by including them into a language pack:
    https://github.com/AnySoftKeyboard/LanguagePack

    Put the resulting file into
    languages/<lang>/pack/src/main/res/xml/<layout>.xml and edit the project
    accordingly.
    """
    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)

    ET = ElementTree
    namespaces = {
            'xmlns:android': 'http://schemas.android.com/apk/res/android',
            'xmlns:ask': 'http://schemas.android.com/apk/res-auto',
            }
    kbdelem = ET.Element ('Keyboard', attrib=namespaces)
    for l, r in keyboard:
        # exclude special buttons
        buttons = list (filter (lambda x: isinstance (x, LetterButton) and not layout.isModifier (frozenset ([x])), chain (l, r)))
        if not buttons:
            continue

        i = keyboard.getRow (buttons[0])
        attrib = {'android:keyWidth': f'{100/len (buttons):.2f}%p'}
        if i == len (keyboard.rows)-1:
            # ignore the bottom row (mostly control characters), generic row is provided below
            continue
        elif i == 0:
            # special top row
            attrib['android:rowEdgeFlags'] = 'top'
            attrib['android:keyHeight'] = '@integer/key_short_height'
        rowelem = ET.SubElement (kbdelem, 'Row', attrib=attrib)

        for btn in buttons:
            # android cannot process multiple characters per button, thus find
            # a composed version (NFC) if possible
            buttonText = [unicodedata.normalize ('NFC', x) if x is not None else '' for x in layout.getButtonText (btn)]
            for t in buttonText:
                if len (t) > 1:
                    logging.info (f'button {btn} has text with len>1 {t}, verify output')
            attrib = {
                    'android:codes': ','.join (map (lambda x: str (ord (x)), buttonText[0])),
                    'android:keyLabel': buttonText[0],
                    'android:popupCharacters': ''.join (buttonText[1:]),
                    # limit the number of hint characters shown
                    'ask:hintLabel': ''.join (buttonText[1:3]),
                    }
            keyelem = ET.SubElement (rowelem, 'Key', attrib=attrib)

    # add generic bottom row
    rowelem = ET.SubElement (kbdelem, 'Row', {'android:rowEdgeFlags': 'bottom', 'android:keyHeight': '@integer/key_normal_height'})
    for attrib in [
            # return
            {'ask:isFunctional': 'true', 'android:keyWidth': '25%p', 'android:codes': '10', 'android:keyEdgeFlags': 'left'},
            # space
            {'ask:isFunctional': 'true', 'android:keyWidth': '50%p', 'android:codes': '32'},
            # backspace
            {'ask:isFunctional': 'true', 'android:keyWidth': '25%p', 'android:codes': '-5', 'android:keyEdgeFlags': 'right', 'android:isRepeatable': 'true'},
            ]:
        ET.SubElement (rowelem, 'Key', )

    tree = ET.ElementTree (kbdelem)
    tree.write (args.output, encoding='utf-8', xml_declaration=True)

def yamlload (s):
    try:
        with open (s) as fd:
            return yaml.safe_load (fd)
    except FileNotFoundError:
        raise argparse.ArgumentTypeError(f'Cannot open file {s}')

def render ():
    parser = argparse.ArgumentParser(description='Render keyboard into output format.')
    parser.add_argument('-l', '--layout', metavar='LAYOUT', help='Keyboard layout name')
    parser.add_argument('-k', '--keyboard', metavar='KEYBOARD',
            default='ibmpc105', help='Physical keyboard name')
    subparsers = parser.add_subparsers()
    sp = subparsers.add_parser('svg')
    sp.add_argument('-s', '--style',
            metavar='FILE',
            default=pkg_resources.resource_stream (__package__, 'data/render-svg.css'),
            # pkg_resources returns bytes(), so we’ll need to decode to unicode
            # ourselves
            type=argparse.FileType('rb'),
            help='Include external stylesheet into SVG')
    sp.add_argument('--heatmap',
            metavar='FILE',
            type=yamlload,
            help='Highlight keys based on heatmap data')
    sp.set_defaults (func=renderSvg)
    sp = subparsers.add_parser('xmodmap')
    sp.set_defaults (func=renderXmodmap)
    sp = subparsers.add_parser('keyman')
    sp.set_defaults (func=renderKeyman)
    sp = subparsers.add_parser('ask')
    sp.set_defaults (func=renderAsk)
    parser.add_argument('output', metavar='FILE', help='Output file')

    logging.basicConfig (level=logging.INFO)
    args = parser.parse_args()

    return args.func (args)

