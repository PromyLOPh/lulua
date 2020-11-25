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
from xml.etree import ElementTree as ET

import svgwrite
import yaml

from .layout import LITTLE, RING, MIDDLE, INDEX, THUMB, GenericLayout, defaultLayouts
from .writer import Writer
from .keyboard import defaultKeyboards, LetterButton
from .util import first, displayText
from .winkbd import qwertyScancodeToVk, VirtualKey, WChar, makeDriverSources

RendererSettings = namedtuple ('RendererSetting', ['buttonMargin', 'middleGap', 'buttonWidth', 'rounded', 'shadowOffset', 'markerStroke'])

class Renderer:
    """ Keyboard to SVG renderer """

    __slots__ = ('keyboard', 'layout', 'settings', 'writer', 'keyHighlight')

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

    def render (self):
        """ Render the entire layout, return single SVG <g> container and its (width, height) """
        settings = self.settings

        btnToPos, (width, height) = self._calcDimensions (self.keyboard)

        g = svgwrite.container.Group ()

        # use multiple layers to get overlapping right
        gCapShadow = svgwrite.container.Group ()
        gCapShadow.attribs['class'] = 'cap-shadow'
        g.add (gCapShadow)
        gCap = svgwrite.container.Group ()
        gCap.attribs['class'] = 'cap'
        g.add (gCap)
        gHighlight = svgwrite.container.Group ()
        gHighlight.attribs['class'] = 'highlight'
        g.add (gHighlight)
        gLabel = svgwrite.container.Group ()
        gLabel.attribs['class'] = 'label'
        g.add (gLabel)

        for btn in self.keyboard.keys ():
            # map modifier keys to arrows, they cannot have any text
            mod = frozenset ([btn])
            isModifier = self.layout.isModifier (mod)
            if isModifier:
                layerToArrow = {1: '⭡', 2: '⭧', 3: '⭨'}
                i, layer = self.layout.modifierToLayer (mod)
                buttonText = [layerToArrow[i]]
            else:
                buttonText = list (map (displayText, self.layout.getButtonText (btn)))

            btnWidth = self.buttonWidth (btn)
            btnPos = btnToPos[btn]

            if any (buttonText):
                hand, finger = self.writer.getHandFinger (btn)
                extraClass = f'finger-{finger.name.lower ()} hand-{hand.name.lower ()}'
                gCapShadow.add (self._drawCapShadow (btnWidth, btnPos, extraClass))

            o = self._drawCap (btnWidth, btnPos)
            if not any (buttonText):
                assert 'class' not in o.attribs
                o.attribs['class'] = 'unused'
            gCap.add (o)
            if btn.isMarked:
                gCap.add (self._drawMarker (btnWidth, btnPos))

            highlight = self.keyHighlight.get (btn.name, 0)
            gHighlight.add (self._drawHighlight (highlight, btnWidth, btnPos))

            l = self._drawLabel (buttonText, btnWidth, btnPos)
            if isModifier:
                assert 'class' not in l.attribs
                l.attribs['class'] = 'modifier'
            gLabel.add (l)

        return g, (width, height)

    def _calcDimensions (self, keyboard):
        """ Create button to position map and keyboard dimensions """
        m = {}

        settings = self.settings
        # keyboard dimensions
        maxWidth = 0
        maxHeight = 0
        # current position
        cursor = [0, 0]

        rowWidth = []
        for l, r in self.keyboard:
            for btn in l:
                assert btn not in m
                m[btn] = tuple (cursor)
                cursor[0] += self.buttonWidth (btn) + settings.buttonMargin

            cursor[0] += settings.middleGap

            for btn in r:
                assert btn not in m
                m[btn] = tuple (cursor)
                cursor[0] += self.buttonWidth (btn) + settings.buttonMargin

            # button height is always the same as default width
            cursor[1] += settings.buttonWidth + settings.buttonMargin
            maxWidth = max (cursor[0], maxWidth)
            rowWidth.append (cursor[0])
            cursor[0] = 0
        maxHeight = cursor[1]

        logging.info (f'row width {rowWidth}')

        return m, (maxWidth, maxHeight)

    def _drawCapShadow (self, width, position, extraClass=''):
        xoff, yoff = position
        settings = self.settings
        return svgwrite.shapes.Rect (
                insert=((xoff+settings.shadowOffset), (yoff+settings.shadowOffset)),
                size=(width, settings.buttonWidth),
                rx=settings.rounded,
                ry=settings.rounded,
                class_=extraClass)

    def _drawCap (self, width, position):
        xoff, yoff = position
        settings = self.settings
        return svgwrite.shapes.Rect (
                insert=(xoff, yoff),
                size=(width, settings.buttonWidth),
                rx=settings.rounded,
                ry=settings.rounded)

    def _drawMarker (self, width, position):
        xoff, yoff = position
        settings = self.settings

        g = svgwrite.container.Group ()
        g.attribs['class'] = 'marker'

        start = (xoff+width*0.3, yoff+settings.buttonWidth*0.9)
        end = (xoff+width*0.7, yoff+settings.buttonWidth*0.9)
        # its shadow
        l = svgwrite.shapes.Line (
                map (lambda x: (x+settings.shadowOffset), start),
                map (lambda x: (x+settings.shadowOffset), end),
                stroke_width=settings.markerStroke,
                class_='shadow')
        g.add (l)
        # the marker itself
        l = svgwrite.shapes.Line (
                start,
                end,
                stroke_width=settings.markerStroke)
        g.add (l)
        return g

    def _drawHighlight (self, highlight, width, position):
        xoff, yoff = position
        settings = self.settings
        # make the circle slight smaller to reduce overlap
        r = min (width, settings.buttonWidth)/2*0.9
        return svgwrite.shapes.Circle (
                center=(xoff+width/2, yoff+settings.buttonWidth/2),
                r=r,
                style=f'opacity: {highlight}')

    def _drawLabel (self, buttonText, width, position):
        g = svgwrite.container.Group ()
        xoff, yoff = position
        settings = self.settings

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
                        direction='rtl',
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
                    t.add (svgwrite.text.TSpan (text, class_=style))
                g.add (t)
        return g

    def buttonWidth (self, btn):
        """ Calculate button width """
        return btn.width * self.settings.buttonWidth

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
            ('IBM Plex Sans Arabic', 100, '3rdparty/plex/IBM-Plex-Sans-Arabic/fonts/complete/woff2/IBMPlexSansArabic-Thin.woff2'),
            ('IBM Plex Sans Arabic', 400, '3rdparty/plex/IBM-Plex-Sans-Arabic/fonts/complete/woff2/IBMPlexSansArabic-Regular.woff2')
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

    xorgGetter = lambda x: x.scancode['xorg']

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
                for btn in unique (keyboard.keys (), key=xorgGetter):
                    keycodeMap[btn].append ('NoSymbol')
                continue
            l = layout.layers[i]
            # space button shares the same keycode and must be removed
            for btn in unique (keyboard.keys (), key=xorgGetter):
                if not layout.isModifier (frozenset ([btn])):
                    text = l.layout.get (btn)
                    if not text:
                        text = 'NoSymbol'
                    else:
                        # some keys cannot be represented by unicode
                        # characters and must be mapped
                        specialMap = {
                            '\t': 'Tab',
                            '\n': 'Return',
                            ' ': 'space',
                            '\b': 'BackSpace',
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
            fd.write (f'!! {btn.name}\nkeycode {xorgGetter (btn)} = {v}\n')
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
                    keymanCode = x.scancode['keyman']
                    if keymanCode.startswith ('K_') or keymanCode == 'CAPS':
                        logging.error (f'Keyman does not support custom modifier like {m}. Your layout will not work correctly.')
                        break
                for btn, text in l.layout.items ():
                    comb = ' '.join ([x.scancode['keyman'] for x in m] + [btn.scancode['keyman']])
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

def renderWinKbd (args):
    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)

    if args.layout != 'ar-lulua':
        logging.error (f'due to the delicate relationship between virtual keys and text output this command will probably not produce working files for your layout. Please have a look at renderWinKbd() in {__file__} and fix the code.')
        return

    resPath = pkg_resources.resource_filename (__package__, 'data/winkbd')

    with open (args.output, 'w') as fd:
        fd.write (f'/* This header was auto-generated by {__package__}. Do not modify directly. */\n\n')

        scancodeToVk = dict (qwertyScancodeToVk)
        # Updates for 3rd and 4th layer modifier keys
        scancodeToVk.update ({
            # mod 3
            (0x2B, ): (VirtualKey.OEM_102, ),
            (0x3A, ): (VirtualKey.OEM_102, ),
            # mod 4
            (0x56, ): (VirtualKey.OEM_8, ),
            (0xe0, 0x38): (VirtualKey.OEM_8, ),
            })

        # translate keyboard buttons to text
        def toWindows (s):
            # convert to windows-convention
            if s == '\n':
                s = '\r'
            return s
        wcharMap = []
        for btn in unique (keyboard.keys (), key=lambda x: x.scancode['windows']):
            text = list (layout.getButtonText (btn))

            # skip unused keys
            if len (list (filter (lambda x: x is not None, text))) == 0:
                continue

            mappedText = [toWindows (s) for s in text]
            vk = next (filter (lambda x: isinstance (x, VirtualKey), scancodeToVk[btn.scancode['windows']]))
            wcharMap.append ((vk, 0, mappedText))

        fd.write (makeDriverSources (scancodeToVk, wcharMap))

def renderKeylayout (args):
    """
    For macOS

    See:
    https://developer.apple.com/library/archive/technotes/tn2056/_index.html#//apple_ref/doc/uid/DTS10003085
    """

    logging.info ('MacOS does not support custom modifiers and thus your layout '
            'is probably not going to work.')

    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)
    nextId = 0

    docroot = ET.Element('keyboard', group="0", id="14242", name=layout.name, maxout="3")

    # fixed modifiers (XXX)
    modmapId = nextId
    modmap = ET.SubElement (docroot, 'modifierMap', id=str (modmapId), defaultIndex='0')
    nextId += 1
    for i, keys in enumerate (('', 'anyShift caps?', 'caps', 'anyOption')):
        keymapSelect = ET.SubElement (modmap, 'keyMapSelect', mapIndex=str (i))
        modifier = ET.SubElement (keymapSelect, 'modifier', keys=keys)

    # keymaps
    keymapSetId = nextId
    keymapSet = ET.SubElement (docroot, 'keyMapSet', id=str (keymapSetId))
    nextId += 1
    for i, l in enumerate (layout.layers):
        keymap = ET.SubElement (keymapSet, 'keyMap', index=str (i))
        for btn, text in l.layout.items ():
            ET.SubElement (keymap, 'key', code=str (btn.scancode['macos']), output=text)

    layouts = ET.SubElement (docroot, 'layouts')
    layout = ET.SubElement (layouts, 'layout', first='0', last='0', modifiers=str (modmapId), mapSet=str (keymapSetId))

    decl = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE keyboard PUBLIC "" "file://localhost/System/Library/DTDs/KeyboardLayout.dtd">
"""
    with open (args.output, 'wb') as fd:
        fd.write (decl)
        fd.write (ET.tostring (docroot, encoding='utf-8'))

def renderKlavaro (args):
    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)

    layers = [[], []]

    for l, r in keyboard:
        # exclude special buttons
        buttons = list (filter (lambda x: isinstance (x, LetterButton), chain (l, r)))
        if not buttons:
            continue

        for btn in buttons:
            # cannot process multiple characters per button, thus find a
            # composed version (NFC) if possible
            buttonText = [unicodedata.normalize ('NFC', x) if x is not None else '' for x in layout.getButtonText (btn)]

            # only two layers supported
            for i in (0, 1):
                # empty buttons must be spaces
                layers[i].append (buttonText[i] or ' ')
        for i in (0, 1):
            layers[i].append ('\n')

    with open (args.output, 'w') as fd:
        for l in layers:
            fd.write (''.join (l).strip ('\n'))
            fd.write ('\n')

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
    sp = subparsers.add_parser('winkbd')
    sp.set_defaults (func=renderWinKbd)
    sp = subparsers.add_parser('keylayout')
    sp.set_defaults (func=renderKeylayout)
    sp = subparsers.add_parser('klavaro')
    sp.set_defaults (func=renderKlavaro)
    parser.add_argument('output', metavar='FILE', help='Output file')

    logging.basicConfig (level=logging.INFO)
    args = parser.parse_args()

    return args.func (args)

