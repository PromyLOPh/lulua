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

def renderWinKbd (args):
    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)

    if args.layout != 'ar-lulua':
        logging.error (f'due to the delicate relationship between virtual keys and text output this command will probably not produce working files for your layout. Please have a look at renderWinKbd() in {__file__} and fix the code.')
        return

    resPath = pkg_resources.resource_filename (__package__, 'data/winkbd')

    with open (args.output, 'w') as fd:
        lines = []
        lines.append (f'/* This header was auto-generated by {__package__}. It is included by {resPath}/keyboard.h. Do not modify. */')
        lines.append ('')

        # copied from kbdneo2.c as well
        # XXX: modifier keys are fixed for now
        # maps virtual keys (first value) to shift bitfield value (second value)
        lines.append ('#define MODIFIER_BITS\\')
        lines.append ("""    { VK_SHIFT		,	KBDSHIFT	}, \\
    { VK_CONTROL	,	KBDCTRL		},    \\
    { VK_MENU		,	KBDALT		}, \\
    { VK_OEM_8		,	KBDKANA		}, \\
    { VK_OEM_102	,	16			},""")

        # copied from kbdneo2.c
        # maps a shift bitfield value (array index) to a layer number in
        # virtual key translation (VK_TO_WCHARS, array value)
        lines.append ('#define CHAR_MODIFIERS_MASK 24')
        lines.append ('#define CHAR_MODIFIERS\\')
        lines.append ('\t{ 0, 1, 6, 7, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, 3, 8, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, 2, 4, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, SHFT_INVALID, 5, }')

        # this is the standard layout from windows’ kbd.h (for KBD_TYPE == 4)
        scancodeToVk = {
            'T01': 'ESCAPE',
            'T02': '1',
            'T03': '2',
            'T04': '3',
            'T05': '4',
            'T06': '5',
            'T07': '6',
            'T08': '7',
            'T09': '8',
            'T0A': '9',
            'T0B': '0',
            'T0C': 'OEM_MINUS',
            'T0D': 'OEM_PLUS',
            'T0E': 'BACK',
            'T0F': 'TAB',
            'T10': 'Q',
            'T11': 'W',
            'T12': 'E',
            'T13': 'R',
            'T14': 'T',
            'T15': 'Y',
            'T16': 'U',
            'T17': 'I',
            'T18': 'O',
            'T19': 'P',
            'T1A': 'OEM_4',
            'T1B': 'OEM_6',
            'T1C': 'RETURN',
            'T1D': 'LCONTROL',
            'T1E': 'A',
            'T1F': 'S',
            'T20': 'D',
            'T21': 'F',
            'T22': 'G',
            'T23': 'H',
            'T24': 'J',
            'T25': 'K',
            'T26': 'L',
            'T27': 'OEM_1',
            'T28': 'OEM_7',
            'T29': 'OEM_3',
            'T2A': 'LSHIFT',
            'T2B': 'OEM_5',
            'T2C': 'Z',
            'T2D': 'X',
            'T2E': 'C',
            'T2F': 'V',
            'T30': 'B',
            'T31': 'N',
            'T32': 'M',
            'T33': 'OEM_COMMA',
            'T34': 'OEM_PERIOD',
            'T35': 'OEM_2',
            'T36': 'RSHIFT',
            'T37': 'MULTIPLY',
            'T38': 'LMENU',
            'T39': 'SPACE',
            'T3A': 'CAPITAL',
            'T3B': 'F1',
            'T3C': 'F2',
            'T3D': 'F3',
            'T3E': 'F4',
            'T3F': 'F5',
            'T40': 'F6',
            'T41': 'F7',
            'T42': 'F8',
            'T43': 'F9',
            'T44': 'F10',
            'T45': 'NUMLOCK',
            'T46': 'SCROLL',
            'T47': 'HOME',
            'T48': 'UP',
            'T49': 'PRIOR',
            'T4A': 'SUBTRACT',
            'T4B': 'LEFT',
            'T4C': 'CLEAR',
            'T4D': 'RIGHT',
            'T4E': 'ADD',
            'T4F': 'END',
            'T50': 'DOWN',
            'T51': 'NEXT',
            'T52': 'INSERT',
            'T53': 'DELETE',
            'T54': 'SNAPSHOT',
            'T56': 'OEM_102',
            'T57': 'F11',
            'T58': 'F12',
            'T59': 'CLEAR',
            'T5A': 'OEM_WSCTRL',
            'T5B': 'OEM_FINISH',
            'T5C': 'OEM_JUMP',
            'T5D': 'EREOF',
            'T5E': 'OEM_BACKTAB',
            'T5F': 'OEM_AUTO',
            'T62': 'ZOOM',
            'T63': 'HELP',
            'T64': 'F13',
            'T65': 'F14',
            'T66': 'F15',
            'T67': 'F16',
            'T68': 'F17',
            'T69': 'F18',
            'T6A': 'F19',
            'T6B': 'F20',
            'T6C': 'F21',
            'T6D': 'F22',
            'T6E': 'F23',
            'T6F': 'OEM_PA3',
            'T71': 'OEM_RESET',
            'T73': 'ABNT_C1',
            'T76': 'F24',
            'T7B': 'OEM_PA1',
            'T7C': 'TAB',
            'T7E': 'ABNT_C2',
            'T7F': 'OEM_PA2',

            'X10': 'MEDIA_PREV_TRACK',
            'X19': 'MEDIA_NEXT_TRACK',
            'X1C': 'RETURN',
            'X1D': 'RCONTROL',
            'X20': 'VOLUME_MUTE',
            'X21': 'LAUNCH_APP2',
            'X22': 'MEDIA_PLAY_PAUSE',
            'X24': 'MEDIA_STOP',
            'X2E': 'VOLUME_DOWN',
            'X30': 'VOLUME_UP',
            'X32': 'BROWSER_HOME',
            'X35': 'DIVIDE',
            'X37': 'SNAPSHOT',
            'X38': 'RMENU',
            'X46': 'CANCEL',
            'X47': 'HOME',
            'X48': 'UP',
            'X49': 'PRIOR',
            'X4B': 'LEFT',
            'X4D': 'RIGHT',
            'X4F': 'END',
            'X50': 'DOWN',
            'X51': 'NEXT',
            'X52': 'INSERT',
            'X53': 'DELETE',
            'X5B': 'LWIN',
            'X5C': 'RWIN',
            'X5D': 'APPS',
            'X5E': 'POWER',
            'X5F': 'SLEEP',
            'X65': 'BROWSER_SEARCH',
            'X66': 'BROWSER_FAVORITES',
            'X67': 'BROWSER_REFRESH',
            'X68': 'BROWSER_STOP',
            'X69': 'BROWSER_FORWARD',
            'X6A': 'BROWSER_BACK',
            'X6B': 'LAUNCH_APP1',
            'X6C': 'LAUNCH_MAIL',
            'X6D': 'LAUNCH_MEDIA_SELECT',
            }
        # modifications copied from kbdneo2.c
        # maps modifier keys to oem values used above.
        scancodeToVk.update ({
            # mod 3
            'T2B': 'OEM_102',
            'T3A': 'OEM_102',
            # mod 4
            'X38': 'OEM_8',
            'T56': 'OEM_8',
            })
        for k, v in scancodeToVk.items ():
            lines.append (f'#undef {k}')
            if len (v) == 1:
                # character value if not symbolic
                lines.append (f'#define {k} \'{v}\'')
            else:
                lines.append (f'#define {k} _EQ({v})')
        lines.append ('')

        lines.append ('#define VK_TO_WCH6 \\')
        for btn in unique (keyboard.keys (), key=attrgetter ('windowsScancode')):
            def toUnicode (s):
                if s is None:
                    return 'WCH_NONE'
                elif len (s) != 1:
                    logging.error (f'only single-character strings are supported, ignoring {s}')
                    return 'WCH_NONE'
                elif s == '\n':
                    # convert to windows-convention
                    s = '\r'
                return f'0x{ord (s):x} /*{repr (s)}*/'

            text = list (layout.getButtonText (btn))
            assert len (text) < 7, "supporting six layers only right now"

            # skip unused keys
            if sum (map (lambda x: 1 if x is not None else 0, text)) == 0:
                continue

            # fixed-length array, need padding
            mappedText = [toUnicode (s) for s in text]
            while len (mappedText) < 6:
                mappedText.append ('WCH_NONE')

            vk = scancodeToVk[btn.windowsScancode]
            if len (vk) == 1:
                # character value
                vk = f"'{vk}'"
            else:
                # symbolic value
                vk = f'VK_{vk}'
            mappingStr = ', '.join (mappedText)
            lines.append (f'\t{{ {vk}, 0, {mappingStr} }}, \\')
        # NUL-termination entry is already present in keyboard.c
        lines.append ('\n')

        fd.write ('\n'.join (lines))
    logging.info ('refer to README.rst on how to build a windows driver. '
            f'Template files are located in {resPath}')

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
    parser.add_argument('output', metavar='FILE', help='Output file')

    logging.basicConfig (level=logging.INFO)
    args = parser.parse_args()

    return args.func (args)

