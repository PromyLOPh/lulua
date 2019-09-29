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

import pytest

from .carpalx import Carpalx, models, ModelParams
from .keyboard import defaultKeyboards
from .layout import defaultLayouts, LEFT, RIGHT, INDEX, MIDDLE, RING, LITTLE
from .writer import Writer

strokePathData = [
    # hands
    (('Dl1', 'Dl3', 'Dr7'), 0, 0),
    (('Dl1', 'Dr7', 'Cr7'), 0, 0),
    (('Dr1', 'Dl5', 'Cl1'), 0, 0),

    (('Dl1', 'Dr7', 'Cl1'), 0, 1),
    (('Dr1', 'Bl1', 'Cr1'), 0, 1),

    (('Dr1', 'Br1', 'Cr1'), 0, 2),
    (('Dl1', 'Bl1', 'Cl1'), 0, 2),

    # rows
    (('Dl1', 'Dl3', 'Dr7'), 1, 0),

    (('Dl3', 'Dl1', 'Er4'), 1, 1),
    (('Cl3', 'Dl1', 'Dr4'), 1, 1),
    (('Cl1', 'Cl2', 'El1'), 1, 1),

    (('Dl1', 'Dl1', 'Cr5'), 1, 2),
    (('El1', 'El1', 'Cr5'), 1, 2),

    (('El6', 'Dl1', 'Er4'), 1, 3),

    (('Cl3', 'Dl3', 'Er4'), 1, 4),
    (('Bl3', 'Dl3', 'Er4'), 1, 4),

    (('Dl1', 'Cl3', 'El6'), 1, 5), # aeb
    (('Dr7', 'Cl3', 'Er5'), 1, 5), # hen
    (('Bl1', 'Dl3', 'Bl1'), 1, 5), # XXX not sure about this one

    (('El6', 'Dl3', 'Cl1'), 1, 6), # bdq
    (('El6', 'Cl3', 'Bl1'), 1, 6), # bdq

    (('Dl1', 'El6', 'Cr6'), 1, 7), # abu
    (('Dl1', 'El3', 'Cl3'), 1, 7), # axe

    # fingers
    (('Dl1', 'Dl2', 'Dl3'), 2, 0), # asd
    (('Cr3', 'Cr6', 'Dl1'), 2, 0), # pua

    (('Dl1', 'Dl1', 'Dl3'), 2, 1), # aad
    (('Dl1', 'Dl2', 'Dl2'), 2, 1), # ass
    (('Cr3', 'Cr4', 'Cr4'), 2, 1), # poo
    (('Er4', 'Er4', 'Cl1'), 2, 1), # mmq

    (('El6', 'Cr5', 'Dr7'), 2, 2), # bih
    (('Dl4', 'Dl1', 'Dl3'), 2, 2), # fad

    (('Cr7', 'Dl1', 'Dr5'), 2, 3), # yak
    (('Er5', 'Cl3', 'Cr3'), 2, 3), # nep

    (('Dr5', 'Cl4', 'Cr5'), 2, 4), # kri
    (('Er4', 'Dl1', 'Dr6'), 2, 4), # maj
    (('Dl1', 'El6', 'El2'), 2, 4), # abz
    (('Dl1', 'Dl2', 'Dl1'), 2, 4), # asa
    (('Dl1', 'Dl3', 'Dl1'), 2, 4), # ada

    (('El4', 'Cl3', 'Cl3'), 2, 5), # cee
    (('Dr4', 'Dr4', 'Cr4'), 2, 5), # llo
    (('El6', 'Cl4', 'El6'), 2, 5), # brb

    (('Dl1', 'El6', 'Cl4'), 2, 6), # abr
    (('El6', 'Dl3', 'Cl3'), 2, 6), # bde
    (('El6', 'El5', 'El2'), 2, 6), # bvz

    (('Cl5', 'Dl4', 'El6'), 2, 7), # tfb
    (('Dl3', 'Cl3', 'El4'), 2, 7), # dec
    ]

# Testing components, since they are independent
@pytest.mark.parametrize("t, i, expect", strokePathData)
def test_strokePath (t, i, expect):
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts['ar-linux'].specialize (keyboard)
    writer = Writer (layout)
    c = Carpalx (models['mod01'], writer)
    t = tuple (map (keyboard.find, t))
    assert c._strokePath (t)[i] == expect

# null model: all parameters are zero
nullmodel = ModelParams (
    kBPS = (0, 0, 0),
    k123S = (0, 0, 0, 0),
    # w0, wHand, wRow, wFinger
    w0HRF = (0, 0, 0, 0),
    pHand = {LEFT: 0, RIGHT: 0},
    pRow = (0, 0),
    # symmetric penalties
    pFinger = {
        LEFT: {
            INDEX: 0,
            MIDDLE: 0,
            RING: 0,
            LITTLE: 0,
            },
        RIGHT: {
            INDEX: 0,
            MIDDLE: 0,
            RING: 0,
            LITTLE: 0,
            },
        },
    # fHand, fRow, fFinger
    fHRF = (0, 0, 0),
    # baseline key effort
    baselineEffort = {
        'Bl1': 0,
        'Bl2': 0,
        'Bl3': 0,
        'Bl4': 0,
        'Bl5': 0,
        'Bl6': 0,
        'Bl7': 0,
        'Br6': 0,
        'Br5': 0,
        'Br4': 0,
        'Br3': 0,
        'Br2': 0,
        'Br1': 0,

        'Cl1': 0,
        'Cl2': 0,
        'Cl3': 0,
        'Cl4': 0,
        'Cl5': 0,
        'Cr7': 0,
        'Cr6': 0,
        'Cr5': 0,
        'Cr4': 0,
        'Cr3': 0,
        'Cr2': 0,
        'Cr1': 0,

        'Dl_caps': 0, # XXX: dito
        'Dl1': 0,
        'Dl2': 0,
        'Dl3': 0,
        'Dl4': 0,
        'Dl5': 0,
        'Dr7': 0,
        'Dr6': 0,
        'Dr5': 0,
        'Dr4': 0,
        'Dr3': 0,
        'Dr2': 0,
        'Dr1': 0, # XXX: not in the original model

        'El_shift': 0,  # XXX: dito
        'El1': 0, # XXX: dito
        'El2': 0,
        'El3': 0,
        'El4': 0,
        'El5': 0,
        'El6': 0,
        'Er5': 0,
        'Er4': 0,
        'Er3': 0,
        'Er2': 0,
        'Er1': 0,
        'Er_shift': 0, # XXX: dito
        },
    )

def test_carpalx ():
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts['ar-linux'].specialize (keyboard)
    writer = Writer (layout)
    c = Carpalx (nullmodel, writer)

    assert c.effort == 0.0
    #c.addTriads (x)
    assert c.effort == 0.0

