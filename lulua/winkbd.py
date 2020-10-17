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
Windows keyboard layout driver generation
"""

from enum import IntEnum
from operator import attrgetter
from itertools import groupby

class CDefEnum (IntEnum):
    @property
    def cdefName (self):
        return f'{self.__class__.__name__.upper()}_{self.name.upper()}'

# Virtal key definitions, see
# https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
vkval = dict (
    LBUTTON = 0x01,
    RBUTTON = 0x02,
    CANCEL = 0x03,
    MBUTTON = 0x04,
    XBUTTON1 = 0x05,
    XBUTTON2 = 0x06,

    BACK = 0x08,
    TAB = 0x09,

    CLEAR = 0x0C,
    RETURN = 0x0D,

    SHIFT = 0x10,
    CONTROL = 0x11,
    MENU = 0x12,
    PAUSE = 0x13,
    CAPITAL = 0x14,

    KANA = 0x15,
    HANGEUL = 0x15,
    HANGUL = 0x15,
    JUNJA = 0x17,
    FINAL = 0x18,
    HANJA = 0x19,
    KANJI = 0x19,

    ESCAPE = 0x1B,

    CONVERT = 0x1C,
    NONCONVERT = 0x1D,
    ACCEPT = 0x1E,
    MODECHANGE = 0x1F,

    SPACE = 0x20,
    PRIOR = 0x21,
    NEXT = 0x22,
    END = 0x23,
    HOME = 0x24,
    LEFT = 0x25,
    UP = 0x26,
    RIGHT = 0x27,
    DOWN = 0x28,
    SELECT = 0x29,
    PRINT = 0x2A,
    EXECUTE = 0x2B,
    SNAPSHOT = 0x2C,
    INSERT = 0x2D,
    DELETE = 0x2E,
    HELP = 0x2F,

    LWIN = 0x5B,
    RWIN = 0x5C,
    APPS = 0x5D,

    SLEEP = 0x5F,

    NUMPAD0 = 0x60,
    NUMPAD1 = 0x61,
    NUMPAD2 = 0x62,
    NUMPAD3 = 0x63,
    NUMPAD4 = 0x64,
    NUMPAD5 = 0x65,
    NUMPAD6 = 0x66,
    NUMPAD7 = 0x67,
    NUMPAD8 = 0x68,
    NUMPAD9 = 0x69,
    MULTIPLY = 0x6A,
    ADD = 0x6B,
    SEPARATOR = 0x6C,
    SUBTRACT = 0x6D,
    DECIMAL = 0x6E,
    DIVIDE = 0x6F,
    F1 = 0x70,
    F2 = 0x71,
    F3 = 0x72,
    F4 = 0x73,
    F5 = 0x74,
    F6 = 0x75,
    F7 = 0x76,
    F8 = 0x77,
    F9 = 0x78,
    F10 = 0x79,
    F11 = 0x7A,
    F12 = 0x7B,
    F13 = 0x7C,
    F14 = 0x7D,
    F15 = 0x7E,
    F16 = 0x7F,
    F17 = 0x80,
    F18 = 0x81,
    F19 = 0x82,
    F20 = 0x83,
    F21 = 0x84,
    F22 = 0x85,
    F23 = 0x86,
    F24 = 0x87,

    NUMLOCK = 0x90,
    SCROLL = 0x91,

    OEM_NEC_EQUAL = 0x92,

    OEM_FJ_JISHO = 0x92,
    OEM_FJ_MASSHOU = 0x93,
    OEM_FJ_TOUROKU = 0x94,
    OEM_FJ_LOYA = 0x95,
    OEM_FJ_ROYA = 0x96,

    LSHIFT = 0xA0,
    RSHIFT = 0xA1,
    LCONTROL = 0xA2,
    RCONTROL = 0xA3,
    LMENU = 0xA4,
    RMENU = 0xA5,

    BROWSER_BACK = 0xA6,
    BROWSER_FORWARD = 0xA7,
    BROWSER_REFRESH = 0xA8,
    BROWSER_STOP = 0xA9,
    BROWSER_SEARCH = 0xAA,
    BROWSER_FAVORITES = 0xAB,
    BROWSER_HOME = 0xAC,

    VOLUME_MUTE = 0xAD,
    VOLUME_DOWN = 0xAE,
    VOLUME_UP = 0xAF,
    MEDIA_NEXT_TRACK = 0xB0,
    MEDIA_PREV_TRACK = 0xB1,
    MEDIA_STOP = 0xB2,
    MEDIA_PLAY_PAUSE = 0xB3,
    LAUNCH_MAIL = 0xB4,
    LAUNCH_MEDIA_SELECT = 0xB5,
    LAUNCH_APP1 = 0xB6,
    LAUNCH_APP2 = 0xB7,

    OEM_1 = 0xBA,
    OEM_PLUS = 0xBB,
    OEM_COMMA = 0xBC,
    OEM_MINUS = 0xBD,
    OEM_PERIOD = 0xBE,
    OEM_2 = 0xBF,
    OEM_3 = 0xC0,

    ABNT_C1 = 0xC1,
    ABNT_C2 = 0xC2,

    OEM_4 = 0xDB,
    OEM_5 = 0xDC,
    OEM_6 = 0xDD,
    OEM_7 = 0xDE,
    OEM_8 = 0xDF,

    OEM_AX = 0xE1,
    OEM_102 = 0xE2,
    ICO_HELP = 0xE3,
    ICO_00 = 0xE4,

    PROCESSKEY = 0xE5,

    ICO_CLEAR = 0xE6,

    PACKET = 0xE7,

    OEM_RESET = 0xE9,
    OEM_JUMP = 0xEA,
    OEM_PA1 = 0xEB,
    OEM_PA2 = 0xEC,
    OEM_PA3 = 0xED,
    OEM_WSCTRL = 0xEE,
    OEM_CUSEL = 0xEF,
    OEM_ATTN = 0xF0,
    OEM_FINISH = 0xF1,
    OEM_COPY = 0xF2,
    OEM_AUTO = 0xF3,
    OEM_ENLW = 0xF4,
    OEM_BACKTAB = 0xF5,

    ATTN = 0xF6,
    CRSEL = 0xF7,
    EXSEL = 0xF8,
    EREOF = 0xF9,
    PLAY = 0xFA,
    ZOOM = 0xFB,
    NONAME = 0xFC,
    PA1 = 0xFD,
    OEM_CLEAR = 0xFE,

    # invalid
    NULL = 0xFF,
    )

# Add ASCII numbers and letters
for i in range (ord ('0'), ord ('9')+1):
    vkval[f'NUMBER{chr (i)}'] = i
for i in range (ord ('A'), ord ('Z')+1):
    vkval[chr (i)] = i

VirtualKey = CDefEnum ('VirtualKey', vkval)

class VirtualKeyFlag (CDefEnum):
    # The Windows API returns EXT as KEYEVENTF_EXTENDEDKEY, see
    # https://docs.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-keybdinput
    EXT = 0x0100
    MULTIVK = 0x0200
    SPECIAL = 0x0400
    NUMPAD = 0x0800
    UNICODE = 0x1000
    INJECTEDVK = 0x2000
    MAPPEDVK = 0x4000
    BREAK = 0x8000

class WChar (CDefEnum):
    """ Wide character symbols """
    NONE = 0xF000 # unused slot

# Default scancode to VirtualKey translation for qwerty
qwertyScancodeToVk = {
    (0x01, ): (VirtualKey.ESCAPE, ),
    (0x02, ): (VirtualKey.NUMBER1, ),
    (0x03, ): (VirtualKey.NUMBER2, ),
    (0x04, ): (VirtualKey.NUMBER3, ),
    (0x05, ): (VirtualKey.NUMBER4, ),
    (0x06, ): (VirtualKey.NUMBER5, ),
    (0x07, ): (VirtualKey.NUMBER6, ),
    (0x08, ): (VirtualKey.NUMBER7, ),
    (0x09, ): (VirtualKey.NUMBER8, ),
    (0x0A, ): (VirtualKey.NUMBER9, ),
    (0x0B, ): (VirtualKey.NUMBER0, ),
    (0x0C, ): (VirtualKey.OEM_MINUS, ),
    (0x0D, ): (VirtualKey.OEM_PLUS, ),
    (0x0E, ): (VirtualKey.BACK, ),
    (0x0F, ): (VirtualKey.TAB, ),
    (0x10, ): (VirtualKey.Q, ),
    (0x11, ): (VirtualKey.W, ),
    (0x12, ): (VirtualKey.E, ),
    (0x13, ): (VirtualKey.R, ),
    (0x14, ): (VirtualKey.T, ),
    (0x15, ): (VirtualKey.Y, ),
    (0x16, ): (VirtualKey.U, ),
    (0x17, ): (VirtualKey.I, ),
    (0x18, ): (VirtualKey.O, ),
    (0x19, ): (VirtualKey.P, ),
    (0x1A, ): (VirtualKey.OEM_4, ),
    (0x1B, ): (VirtualKey.OEM_6, ),
    (0x1C, ): (VirtualKey.RETURN, ),
    (0x1D, ): (VirtualKey.LCONTROL, ),
    (0x1E, ): (VirtualKey.A, ),
    (0x1F, ): (VirtualKey.S, ),
    (0x20, ): (VirtualKey.D, ),
    (0x21, ): (VirtualKey.F, ),
    (0x22, ): (VirtualKey.G, ),
    (0x23, ): (VirtualKey.H, ),
    (0x24, ): (VirtualKey.J, ),
    (0x25, ): (VirtualKey.K, ),
    (0x26, ): (VirtualKey.L, ),
    (0x27, ): (VirtualKey.OEM_1, ),
    (0x28, ): (VirtualKey.OEM_7, ),
    (0x29, ): (VirtualKey.OEM_3, ),
    (0x2A, ): (VirtualKey.LSHIFT, ),
    (0x2B, ): (VirtualKey.OEM_5, ),
    (0x2C, ): (VirtualKey.Z, ),
    (0x2D, ): (VirtualKey.X, ),
    (0x2E, ): (VirtualKey.C, ),
    (0x2F, ): (VirtualKey.V, ),
    (0x30, ): (VirtualKey.B, ),
    (0x31, ): (VirtualKey.N, ),
    (0x32, ): (VirtualKey.M, ),
    (0x33, ): (VirtualKey.OEM_COMMA, ),
    (0x34, ): (VirtualKey.OEM_PERIOD, ),
    (0x35, ): (VirtualKey.OEM_2, ),
    (0x36, ): (VirtualKey.RSHIFT, VirtualKeyFlag.EXT), # Right-hand shift needs ext bit (XXX why?)
    (0x37, ): (VirtualKey.MULTIPLY, VirtualKeyFlag.MULTIVK),
    (0x38, ): (VirtualKey.LMENU, ),
    (0x39, ): (VirtualKey.SPACE, ),
    (0x3A, ): (VirtualKey.CAPITAL, ),
    (0x3B, ): (VirtualKey.F1, ),
    (0x3C, ): (VirtualKey.F2, ),
    (0x3D, ): (VirtualKey.F3, ),
    (0x3E, ): (VirtualKey.F4, ),
    (0x3F, ): (VirtualKey.F5, ),
    (0x40, ): (VirtualKey.F6, ),
    (0x41, ): (VirtualKey.F7, ),
    (0x42, ): (VirtualKey.F8, ),
    (0x43, ): (VirtualKey.F9, ),
    (0x44, ): (VirtualKey.F10, ),
    (0x45, ): (VirtualKey.NUMLOCK, VirtualKeyFlag.EXT, VirtualKeyFlag.MULTIVK),
    (0x46, ): (VirtualKey.SCROLL, VirtualKeyFlag.MULTIVK),
    (0x47, ): (VirtualKey.HOME, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x48, ): (VirtualKey.UP, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x49, ): (VirtualKey.PRIOR, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x4A, ): (VirtualKey.SUBTRACT, ),
    (0x4B, ): (VirtualKey.LEFT, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x4C, ): (VirtualKey.CLEAR, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x4D, ): (VirtualKey.RIGHT, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x4E, ): (VirtualKey.ADD, ),
    (0x4F, ): (VirtualKey.END, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x50, ): (VirtualKey.DOWN, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x51, ): (VirtualKey.NEXT, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x52, ): (VirtualKey.INSERT, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x53, ): (VirtualKey.DELETE, VirtualKeyFlag.NUMPAD, VirtualKeyFlag.SPECIAL),
    (0x54, ): (VirtualKey.SNAPSHOT, ),
    (0x56, ): (VirtualKey.OEM_102, ),
    (0x57, ): (VirtualKey.F11, ),
    (0x58, ): (VirtualKey.F12, ),
    (0x59, ): (VirtualKey.CLEAR, ),
    (0x5A, ): (VirtualKey.OEM_WSCTRL, ),
    (0x5B, ): (VirtualKey.OEM_FINISH, ),
    (0x5C, ): (VirtualKey.OEM_JUMP, ),
    (0x5D, ): (VirtualKey.EREOF, ),
    (0x5E, ): (VirtualKey.OEM_BACKTAB, ),
    (0x5F, ): (VirtualKey.OEM_AUTO, ),
    (0x62, ): (VirtualKey.ZOOM, ),
    (0x63, ): (VirtualKey.HELP, ),
    (0x64, ): (VirtualKey.F13, ),
    (0x65, ): (VirtualKey.F14, ),
    (0x66, ): (VirtualKey.F15, ),
    (0x67, ): (VirtualKey.F16, ),
    (0x68, ): (VirtualKey.F17, ),
    (0x69, ): (VirtualKey.F18, ),
    (0x6A, ): (VirtualKey.F19, ),
    (0x6B, ): (VirtualKey.F20, ),
    (0x6C, ): (VirtualKey.F21, ),
    (0x6D, ): (VirtualKey.F22, ),
    (0x6E, ): (VirtualKey.F23, ),
    (0x6F, ): (VirtualKey.OEM_PA3, ),
    (0x71, ): (VirtualKey.OEM_RESET, ),
    (0x73, ): (VirtualKey.ABNT_C1, ),
    (0x76, ): (VirtualKey.F24, ),
    (0x7B, ): (VirtualKey.OEM_PA1, ),
    (0x7C, ): (VirtualKey.TAB, ),
    (0x7E, ): (VirtualKey.ABNT_C2, ),
    (0x7F, ): (VirtualKey.OEM_PA2, ),

    # Prefixed codes: E0
    (0xe0, 0x10): (VirtualKey.MEDIA_PREV_TRACK, VirtualKeyFlag.EXT),
    (0xe0, 0x19): (VirtualKey.MEDIA_NEXT_TRACK, VirtualKeyFlag.EXT),
    (0xe0, 0x1C): (VirtualKey.RETURN, VirtualKeyFlag.EXT),
    (0xe0, 0x1D): (VirtualKey.RCONTROL, VirtualKeyFlag.EXT),
    (0xe0, 0x20): (VirtualKey.VOLUME_MUTE, VirtualKeyFlag.EXT),
    (0xe0, 0x21): (VirtualKey.LAUNCH_APP2, VirtualKeyFlag.EXT),
    (0xe0, 0x22): (VirtualKey.MEDIA_PLAY_PAUSE, VirtualKeyFlag.EXT),
    (0xe0, 0x24): (VirtualKey.MEDIA_STOP, VirtualKeyFlag.EXT),
    (0xe0, 0x2E): (VirtualKey.VOLUME_DOWN, VirtualKeyFlag.EXT),
    (0xe0, 0x30): (VirtualKey.VOLUME_UP, VirtualKeyFlag.EXT),
    (0xe0, 0x32): (VirtualKey.BROWSER_HOME, VirtualKeyFlag.EXT),
    (0xe0, 0x35): (VirtualKey.DIVIDE, VirtualKeyFlag.EXT),
    (0xe0, 0x37): (VirtualKey.SNAPSHOT, VirtualKeyFlag.EXT),
    (0xe0, 0x38): (VirtualKey.RMENU, VirtualKeyFlag.EXT),
    (0xe0, 0x46): (VirtualKey.CANCEL, VirtualKeyFlag.EXT),
    (0xe0, 0x47): (VirtualKey.HOME, VirtualKeyFlag.EXT),
    (0xe0, 0x48): (VirtualKey.UP, VirtualKeyFlag.EXT),
    (0xe0, 0x49): (VirtualKey.PRIOR, VirtualKeyFlag.EXT),
    (0xe0, 0x4B): (VirtualKey.LEFT, VirtualKeyFlag.EXT),
    (0xe0, 0x4D): (VirtualKey.RIGHT, VirtualKeyFlag.EXT),
    (0xe0, 0x4F): (VirtualKey.END, VirtualKeyFlag.EXT),
    (0xe0, 0x50): (VirtualKey.DOWN, VirtualKeyFlag.EXT),
    (0xe0, 0x51): (VirtualKey.NEXT, VirtualKeyFlag.EXT),
    (0xe0, 0x52): (VirtualKey.INSERT, VirtualKeyFlag.EXT),
    (0xe0, 0x53): (VirtualKey.DELETE, VirtualKeyFlag.EXT),
    (0xe0, 0x5B): (VirtualKey.LWIN, VirtualKeyFlag.EXT),
    (0xe0, 0x5C): (VirtualKey.RWIN, VirtualKeyFlag.EXT),
    (0xe0, 0x5D): (VirtualKey.APPS, VirtualKeyFlag.EXT),
    # XXX what is VK_POWER’s value?
    #(0xe0, 0x5E): (VirtualKey.POWER, VirtualKeyFlag.EXT),
    (0xe0, 0x5F): (VirtualKey.SLEEP, VirtualKeyFlag.EXT),
    (0xe0, 0x65): (VirtualKey.BROWSER_SEARCH, VirtualKeyFlag.EXT),
    (0xe0, 0x66): (VirtualKey.BROWSER_FAVORITES, VirtualKeyFlag.EXT),
    (0xe0, 0x67): (VirtualKey.BROWSER_REFRESH, VirtualKeyFlag.EXT),
    (0xe0, 0x68): (VirtualKey.BROWSER_STOP, VirtualKeyFlag.EXT),
    (0xe0, 0x69): (VirtualKey.BROWSER_FORWARD, VirtualKeyFlag.EXT),
    (0xe0, 0x6A): (VirtualKey.BROWSER_BACK, VirtualKeyFlag.EXT),
    (0xe0, 0x6B): (VirtualKey.LAUNCH_APP1, VirtualKeyFlag.EXT),
    (0xe0, 0x6C): (VirtualKey.LAUNCH_MAIL, VirtualKeyFlag.EXT),
    (0xe0, 0x6D): (VirtualKey.LAUNCH_MEDIA_SELECT, VirtualKeyFlag.EXT),

    # Prefixed codes: E1
    (0xe1, 0x1d): (VirtualKey.PAUSE, ),
    }

def enumToCDefine (e):
    """
    Transform Python Enum into a bunch of #define statements
    """
    prefix = e.__name__.upper ()
    ret = [f'/* {e.__name__} */']
    for name, member in e.__members__.items ():
        ret.append (f'#define {member.cdefName} (0x{member:X}u)')
    ret.append ('')
    return '\n'.join (ret)

def enumOr (v):
    """
    Turn list of enum values v into C OR statement
    """
    return ' | '.join (map (attrgetter ('cdefName'), v))
    
def scancodeToVkTables (m):
    """
    Transform scancode to virtual key map m into C arrays
    """
    # non-prefixed scancodes
    ret = ['/* mappings from scancode to virtual key */',
            '/* non-prefixed scancodes */',
            'static unsigned short ausVK[] = {']
    for i in range (0, 0x7f+1):
        v = m.get ((i, ), (VirtualKey.NULL, ))
        ret.append (f'\t /* {i:02X} */ {enumOr (v)},')
    ret.append ('\t};\n')

    # now E0 and E1, must be sorted
    for escape in (0xe0, 0xe1):
        ret.extend ([f'/* scancodes prefixed by {escape:X} */', f'static VSC_VK a{escape:X}VscToVk[] = {{'])
        f = lambda x: len (x[0]) == 2 and x[0][0] == escape
        for k, v in sorted (filter (f, m.items ()), key=lambda x: x[0]):
            ret.append (f'\t{{ 0x{k[1]:x}, {enumOr (v)} }},')
        ret.append ('\t};\n')

    return '\n'.join (ret)

qwertyScancodeToName = {
    (0x01, ): "Esc",
    (0x0e, ): "Backspace",
    (0x0f, ): "Tab",
    (0x1c, ): "Enter",
    (0x1d, ): "Ctrl",
    (0x2a, ): "Shift",
    (0x36, ): "Right Shift",
    (0x37, ): "Num *",
    (0x38, ): "Alt",
    (0x39, ): "Space",
    (0x3a, ): "Caps Lock",
    (0x3b, ): "F1",
    (0x3c, ): "F2",
    (0x3d, ): "F3",
    (0x3e, ): "F4",
    (0x3f, ): "F5",
    (0x40, ): "F6",
    (0x41, ): "F7",
    (0x42, ): "F8",
    (0x43, ): "F9",
    (0x44, ): "F10",
    (0x45, ): "Pause",
    (0x46, ): "Scroll Lock",
    (0x47, ): "Num 7",
    (0x48, ): "Num 8",
    (0x49, ): "Num 9",
    (0x4a, ): "Num -",
    (0x4b, ): "Num 4",
    (0x4c, ): "Num 5",
    (0x4d, ): "Num 6",
    (0x4e, ): "Num +",
    (0x4f, ): "Num 1",
    (0x50, ): "Num 2",
    (0x51, ): "Num 3",
    (0x52, ): "Num 0",
    (0x53, ): "Num Del",
    (0x54, ): "Sys Req",
    (0x57, ): "F11",
    (0x58, ): "F12",
    (0x7c, ): "F13",
    (0x7d, ): "F14",
    (0x7e, ): "F15",
    (0x7f, ): "F16",
    (0x80, ): "F17",
    (0x81, ): "F18",
    (0x82, ): "F19",
    (0x83, ): "F20",
    (0x84, ): "F21",
    (0x85, ): "F22",
    (0x86, ): "F23",
    (0x87, ): "F24",

    # With E0 prefix
    (0xe0, 0x1c): "Num Enter",
    (0xe0, 0x1d): "Right Ctrl",
    (0xe0, 0x35): "Num /",
    (0xe0, 0x37): "Prnt Scrn",
    (0xe0, 0x38): "Right Alt",
    (0xe0, 0x45): "Num Lock",
    (0xe0, 0x46): "Break",
    (0xe0, 0x47): "Home",
    (0xe0, 0x48): "Up",
    (0xe0, 0x49): "Page Up",
    (0xe0, 0x4b): "Left",
    (0xe0, 0x4d): "Right",
    (0xe0, 0x4f): "End",
    (0xe0, 0x50): "Down",
    (0xe0, 0x51): "Page Down",
    (0xe0, 0x52): "Insert",
    (0xe0, 0x53): "Delete",
    (0xe0, 0x54): "<00>",
    (0xe0, 0x56): "Help",
    (0xe0, 0x5b): "Left Windows",
    (0xe0, 0x5c): "Right Windows",
    (0xe0, 0x5d): "Application",
    }

def scancodeToName (m):
    """ Create virtual scancode to name mapping tables """

    ret = []

    # first unprefixed keys
    ret.extend (['/* Virtual scancode to key name */',
            'static VSC_LPWSTR aKeyNames[] = {'])
    f = lambda x: len (x[0]) == 1
    for k, v in sorted (filter (f, m.items ()), key=lambda x: x[0]):
        ret.append (f'\t{{0x{k[0]:02x}, L"{v}"}},')
    ret.extend (['\t{0x00, NULL},', '};', ''])

    ret.extend (['/* Virtual scan code (E0 prefixed) to key name */',
            'static VSC_LPWSTR aKeyNamesExt[] = {'])
    f = lambda x: len (x[0]) == 2 and x[0][0] == 0xe0
    for k, v in sorted (filter (f, m.items ()), key=lambda x: x[0]):
        ret.append (f'\t{{0x{k[1]:02x}, L"{v}"}},')
    ret.extend (['\t{0x00, NULL},', '};', ''])

    return '\n'.join (ret)

vkToBitsTable = [
    (VirtualKey.SHIFT, (1<<0)),
    (VirtualKey.CONTROL, (1<<1)),
    (VirtualKey.MENU, (1<<2)),
    (VirtualKey.OEM_8, (1<<3)),
    (VirtualKey.OEM_102, (1<<4)),
    ]

def vkToBits ():
    ret = ['/* maps virtual keys (first value) to shift bitfield value (second value) */',
            'static VK_TO_BIT aVkToBits[] = {']
    for vk, bits in vkToBitsTable:
        ret.append (f'\t{{{vk.cdefName}, 0x{bits:x}}},')
    ret.append ('\t{0, 0x0}')
    ret.append ('\t};\n')
    return '\n'.join (ret)

def charModifiers ():
    # array index is layer number
    vkToLayer = list (map (set, [
        tuple (), # base
        (VirtualKey.SHIFT, ),
        (VirtualKey.OEM_102, ),
        (VirtualKey.OEM_8, ),
        (VirtualKey.SHIFT, VirtualKey.OEM_102),
        (VirtualKey.OEM_8, VirtualKey.OEM_102),
        (VirtualKey.CONTROL, ),
        (VirtualKey.SHIFT, VirtualKey.CONTROL),
        (VirtualKey.SHIFT, VirtualKey.OEM_8),
        ]))
    disabled = 0x0F

    ret = ['/* maps a shift bitfield value (array index) to a layer number in',
            'virtual key translation (VK_TO_WCHARS, array value) */',
            'static MODIFIERS CharModifiers = {',
            '\t&aVkToBits[0],',
            '\t24,',
            ]
    ret.append ('\t{')
    for i in range (25):
        keys = set (map (lambda x: x[0], filter (lambda x: i & x[1], vkToBitsTable)))
        try:
            layer = vkToLayer.index (keys)
        except ValueError:
            layer = disabled
        keysComment = enumOr (keys) if not layer == disabled else "disabled"
        ret.append (f'\t\t0x{layer:x}, /* {keysComment} */')
    ret.append ('\t}};\n')
    return '\n'.join (ret)

def vkToWchar (m):
    """ Mapping from virtual key to character """

    ret = []
    retTbl = ['/* table of virtual key to wchar mapping tables */',
            'static VK_TO_WCHAR_TABLE aVkToWcharTable[] = {']

    def generate (n, g, defPrefix=''):
        defname = f'aVkToWch{defPrefix}{n}'
        ret.extend ([f'/* map virtual key to flags and {n} unicode output characters */',
                f'static VK_TO_WCHARS{n} {defname}[] = {{'])
        for vk, flags, chars in g:
            def toRepr (s):
                if s is None:
                    return WChar.NONE.cdefName
                elif len (s) != 1:
                    # everything else belongs to ligature tables, which we
                    # don’t support.
                    raise Exception (f'only single-character strings are supported ({s!r})')
                else:
                    return f'0x{ord (s):04X}u /*{repr (s)}*/'
            chars = ', '.join (map (toRepr, chars))
            ret.append (f'\t{{{vk.cdefName}, {flags}, {{{chars}}}}},')
        ret.extend ([f'\t{{0, 0, {{{("0, "*n)}}}}},', '\t};', ''])
        # add the new table
        retTbl.append (f'\t{{(PVK_TO_WCHARS1) {defname}, {n}, sizeof({defname}[0])}},')

    f = lambda x: len (x[2])
    m = groupby (sorted (m, key=f), key=f)
    for n, g in m:
        generate (n, g)

    # We are almost always going to need the numpad keys. They also need to be
    # last, so translation from string to virtual key does not map them.
    numpad = [
        (VirtualKey.NUMPAD0, 0, '0'),
        (VirtualKey.NUMPAD1, 0, '1'),
        (VirtualKey.NUMPAD2, 0, '2'),
        (VirtualKey.NUMPAD3, 0, '3'),
        (VirtualKey.NUMPAD4, 0, '4'),
        (VirtualKey.NUMPAD5, 0, '5'),
        (VirtualKey.NUMPAD6, 0, '6'),
        (VirtualKey.NUMPAD7, 0, '7'),
        (VirtualKey.NUMPAD8, 0, '8'),
        (VirtualKey.NUMPAD9, 0, '9'),
        ]
    generate (1, numpad, 'Num')

    retTbl.extend (['\t{NULL, 0, 0},', '\t};'])
    return '\n'.join (ret + retTbl)

typedefs = """
#include <wchar.h>

typedef struct {
    unsigned char Vk;
    unsigned char ModBits;
} VK_TO_BIT, *PVK_TO_BIT;

typedef struct {
    PVK_TO_BIT pVkToBit;
    unsigned short wMaxModBits;
    unsigned char ModNumber[];
} MODIFIERS, *PMODIFIERS;

typedef struct _VSC_VK {
    unsigned char Vsc;
    unsigned short Vk;
} VSC_VK, *PVSC_VK;
"""

for n in range (1, 9):
    typedefs += f"""
typedef struct _VK_TO_WCHARS{n} {{
    unsigned char VirtualKey;
    unsigned char Attributes;
    wchar_t wch[{n}];
}} VK_TO_WCHARS{n}, *PVK_TO_WCHARS{n};
"""

for n in (1, ):
    typedefs += f"""
typedef struct _LIGATURE{n} {{
    unsigned char VirtualKey;
    unsigned short ModificationNumber;
    wchar_t wch[{n}];
}} LIGATURE{n}, *PLIGATURE{n};
"""

typedefs += """
typedef struct _VK_TO_WCHAR_TABLE {
    PVK_TO_WCHARS1 pVkToWchars;
    unsigned char nModifications;
    unsigned char cbSize;
} VK_TO_WCHAR_TABLE, *PVK_TO_WCHAR_TABLE;

typedef struct {
    unsigned long dwBoth;
    wchar_t wchComposed;
    unsigned short uFlags;
} DEADKEY, *PDEADKEY;

typedef struct {
    unsigned char vsc;
    wchar_t *pwsz;
} VSC_LPWSTR, *PVSC_LPWSTR;

typedef struct tagKbdLayer {
    /*
     * Modifier keys
     */
    PMODIFIERS pCharModifiers;

    /*
     * Characters
     */
    PVK_TO_WCHAR_TABLE pVkToWcharTable;  // ptr to tbl of ptrs to tbl

    /*
     * Diacritics
     */
    PDEADKEY pDeadKey;

    /*
     * Names of Keys
     */
    PVSC_LPWSTR pKeyNames;
    PVSC_LPWSTR pKeyNamesExt;
    wchar_t **pKeyNamesDead;

    /*
     * Scan codes to Virtual Keys
     */
    unsigned short *pusVSCtoVK;
    unsigned char    bMaxVSCtoVK;
    PVSC_VK pVSCtoVK_E0;  // Scancode has E0 prefix
    PVSC_VK pVSCtoVK_E1;  // Scancode has E1 prefix

    /*
     * Locale-specific special processing
     */
    unsigned long fLocaleFlags;

    /*
     * Ligatures
     */
    unsigned char       nLgMax;
    unsigned char       cbLgEntry;
    PLIGATURE1 pLigature;

    /*
     * Type and subtype. These are optional.
     */
    unsigned long dwType;     // Keyboard Type
    unsigned long dwSubType;  // Keyboard SubType: may contain OemId
} KBDTABLES, *PKBDTABLES;
"""

entrypoint = """
#define KBD_VERSION (1)

static KBDTABLES KbdTables = {
    pCharModifiers: &CharModifiers,

    pVkToWcharTable: aVkToWcharTable,

    pDeadKey: NULL,

    pKeyNames: aKeyNames,
    pKeyNamesExt: aKeyNamesExt,
    pKeyNamesDead: NULL,

    pusVSCtoVK: ausVK,
    bMaxVSCtoVK: sizeof(ausVK) / sizeof(*ausVK),
    pVSCtoVK_E0: aE0VscToVk,
    pVSCtoVK_E1: aE1VscToVk,

    fLocaleFlags: (0 & 0xffffUL) | ((KBD_VERSION & 0xffffUL) << 16),

    nLgMax: 0,
    cbLgEntry: 0,
    pLigature: NULL,

    dwType: 0,
    dwSubType: 0,
};

/* The main entry point of the driver
 */
PKBDTABLES KbdLayerDescriptor() {
    return &KbdTables;
}
"""

def makeDriverSources (scancodes, charmap):
    """
    Create a single file keyboard driver.

    scancodes is a mapping like qwertyScancodeToVk from virtual scancode to
    virtual key. charmap is a list of triples (virtual key, flags, [list of
    strings]).
    """

    ret = [
        typedefs,
        enumToCDefine (VirtualKey),
        enumToCDefine (VirtualKeyFlag),
        enumToCDefine (WChar),
        scancodeToVkTables (scancodes),
        scancodeToName (qwertyScancodeToName),
        vkToBits (),
        charModifiers (),
        vkToWchar (charmap),
        entrypoint
        ]
    return '\n'.join (ret)

__all__ = ('VirtualKey', 'VirtualKeyFlag')

