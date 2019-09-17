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

import pickle, sys, random, time, logging, argparse
from copy import deepcopy
from typing import List, Tuple, Optional, Text, FrozenSet
from abc import abstractmethod
from operator import itemgetter
from collections import defaultdict
from itertools import chain

from tqdm import tqdm
# work around pypy bug https://bitbucket.org/pypy/pypy/issues/2953/deadlock
tqdm.get_lock().locks = []
import yaml

from .layout import defaultLayouts, ButtonCombination, Layer, KeyboardLayout, GenericLayout
from .carpalx import Carpalx
from .carpalx import model01 as cmodel01
from .writer import Writer
from .util import first
from .keyboard import defaultKeyboards, LetterButton

class Annealer:
    """
    Simulated annealing.

    Override .mutate() to suit your needs. Uses exponential cooling (10^(-progress*factor))

    Inspired by https://github.com/perrygeo/simanneal
    """

    __slots__ = ('state', 'best', 'coolingFactor')

    def __init__ (self, state):
        self.state = state
        self.best = None
        self.coolingFactor = 6

    @abstractmethod
    def mutate (self):
        """ Modify current state, returns energy change """
        raise NotImplementedError ()

    def run (self, steps=10000):
        # this is not the absolute energy, but relative
        energy = 0
        energyMax = energy
        # figure out the max mutation impact, so we can gradually reduce the
        # amount of allowed changes (i.e. simulated annealing)
        energyDiffMax = 0

        self.best = (self.state.copy (), energy)
        bar = tqdm (total=steps, unit='mut', smoothing=0.1)
        for i in range (steps):
            start = time.time ()

            progress = i/steps
            acceptDiff = 10**-(progress*self.coolingFactor)

            prev = (self.state.copy (), energy)
            energyDiff = self.mutate ()
            newEnergy = energy+energyDiff
            energyMax = max (newEnergy, energyMax)
            energyDiffAbs = abs (energyDiff)
            energyDiffMax = max (energyDiffAbs, energyDiffMax)
            relDiff = energyDiffAbs/energyDiffMax if energyDiffMax != 0 else 1

            # accept if the energy is lower or the relative difference is small
            # (decreasing with temperature, avoids running into local minimum)
            if energyDiff < 0 or relDiff < acceptDiff:
                # accept
                if newEnergy < self.best[1]:
                    self.best = (self.state.copy (), newEnergy)
                energy = newEnergy
            else:
                # restore
                self.state, energy = prev

            bar.set_description (desc=f'{energy:5.4f}{energyDiff:+5.4f}{relDiff:+5.4f}({acceptDiff:5.4f}) [{self.best[1]:5.4f},{energyMax:5.4f}{energyDiffMax:+5.4f}]', refresh=False)
            bar.update ()

        return self.best

def mapButton (layout, buttonMap, b : ButtonCombination) -> ButtonCombination:
    (layerNum, _) = layout.modifierToLayer (b.modifier)
    assert len (b.buttons) == 1
    button = first (b.buttons)
    (newLayerNum, newButton) = buttonMap[(layerNum, button)]
    # XXX: this might not be correct for layer changes! use a Writer()
    # instead
    ret = ButtonCombination (layout.layers[newLayerNum].modifier[0], frozenset ([newButton]))
    return ret

class LayoutOptimizerState:
    __slots__ = ('carpalx', 'buttonMap')

    def __init__ (self, carpalx, buttonMap):
        self.carpalx = carpalx
        self.buttonMap = buttonMap

    def copy (self):
        carpalx = self.carpalx.copy ()
        buttonMap = self.buttonMap.copy ()
        return LayoutOptimizerState (carpalx, buttonMap)

class LayoutOptimizer (Annealer):
    """
    Optimize a keyboard layout.

    The state here is
    a) a carpalx instance which knows the current state’s effort/energy
    b) a map (layerNumber: int, button: Button) → (layerNumber: int,
       button: Button)

    b can be used to map each ButtonCombination for each triad to the new
    layout. And these mapped triads can then be fed into carpalx again to
    compute a new effort/energy.

    Since the whole process is pretty slow with lots of triads (and we want to
    have alot) only those affected by a mutation (self.stateToTriad) are
    recomputed via carpalx. This gives a nice speedup of about 10x with 200k
    triads (“it takes a day” → “it takes one (long) coffee break”).
    """

    __slots__ = ('triads', 'allButtons', 'best', 'layout', 'pins', 'stateToTriad')

    def __init__ (self,
            buttonMap,
            triads: List[Tuple[ButtonCombination]],
            layout: KeyboardLayout,
            pins: FrozenSet[Tuple[int, Optional[Text]]],
            writer: Writer):
        carpalx = Carpalx (cmodel01, writer)
        super ().__init__ (LayoutOptimizerState (carpalx, buttonMap))

        self.triads = triads
        self.layout = layout
        self.pins = pins
        self.allButtons = list (buttonMap.keys ())

        # which triads are affected by which state?
        self.stateToTriad = defaultdict (set)
        for i, (t, v) in enumerate (self.triads):
            for comb in t:
                layer, _ = layout.modifierToLayer (comb.modifier)
                assert len (comb.buttons) == 1
                button = first (comb.buttons)
                self.stateToTriad[(layer, button)].add (i)

    def _acceptMutation (self, state, a, b) -> bool:
        if a == b:
            return False

        newa = state[b]
        newb = state[a]

        # respect pins
        if a in self.pins or b in self.pins or \
                (a[0], None) in self.pins and newa[0] != a[0] or \
                (b[0], None) in self.pins and newb[0] != b[0]:
            return False

        return True

    def mutate (self, withEnergy=True):
        """ Single step to find a neighbor """
        buttonMap = self.state.buttonMap
        while True:
            a = random.choice (self.allButtons)
            b = random.choice (self.allButtons)
            if self._acceptMutation (self.state.buttonMap, a, b):
                break
        if not withEnergy:
            buttonMap[b], buttonMap[a] = buttonMap[a], buttonMap[b]
            return

        carpalx = self.state.carpalx
        oldEffort = carpalx.effort
        #logging.info (f'old effort is {oldEffort}')

        # see which *original* buttons are affected by the change, then map all
        # triads according to state, remove them and re-add them after the swap
        affected = set (chain (self.stateToTriad[a], self.stateToTriad[b]))
        for i in affected:
            t, v = self.triads[i]
            newTriad = tuple (mapButton (self.layout, buttonMap, x) for x in t)
            carpalx.removeTriad (newTriad, v)
            #logging.info (f'removing triad {newTriad} {v}')

        #logging.info (f'swapping {buttonMap[a]} and {buttonMap[b]}')
        buttonMap[b], buttonMap[a] = buttonMap[a], buttonMap[b]

        for i in affected:
            t, v = self.triads[i]
            newTriad = tuple (mapButton (self.layout, buttonMap, x) for x in t)
            carpalx.addTriad (newTriad, v)
        newEffort = carpalx.effort
        #logging.info (f'new effort is {newEffort}')

        return newEffort-oldEffort

    def energy (self):
        """ Current system energy """
        return self.state.carpalx.effort

    def _resetEnergy (self):
        # if the user calls mutate(withEnergy=False) (for speed) the initial
        # energy is wrong. thus, we need to recalculate it here.
        carpalx = self.state.carpalx
        buttonMap = self.state.buttonMap
        carpalx.reset ()
        for t, v in self.triads:
            newTriad = tuple (mapButton (self.layout, buttonMap, x) for x in t)
            carpalx.addTriad (newTriad, v)
        logging.info (f'initial effort is {carpalx.effort}')

    def run (self, steps=10000):
        self._resetEnergy ()
        return super().run (steps)

def parsePin (s: Text):
    """ Parse --pin argument """
    pins = []
    for p in s.split (';'):
        p = p.split (',', 1)
        layer = int (p[0])
        button = p[1] if len (p) > 1 else None
        pins.append ((layer, button))
    return frozenset (pins)

def optimize ():
    parser = argparse.ArgumentParser(description='Optimize keyboard layout.')
    parser.add_argument('-l', '--layout', metavar='LAYOUT', help='Keyboard layout name')
    parser.add_argument('-k', '--keyboard', metavar='KEYBOARD',
            default='ibmpc105', help='Physical keyboard name')
    parser.add_argument('--triad-limit', dest='triadLimit', metavar='NUM',
            type=int, default=0, help='Limit number of triads to use')
    parser.add_argument('-n', '--steps', type=int, default=10000, help='Number of iterations')
    parser.add_argument('-r', '--randomize', action='store_true', help='Randomize layout before optimizing')
    parser.add_argument('-p', '--pin', type=parsePin, help='Pin these layers/buttons')

    args = parser.parse_args()

    logging.basicConfig (level=logging.INFO)

    stats = pickle.load (sys.stdin.buffer)

    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)
    writer = Writer (layout)
    triads = stats['triads'].triads

    logging.info (f'using keyboard {keyboard.name}, layout {layout.name} '
            f'and {args.triadLimit}/{len (triads)} triads')

    # limit number of triads to increase performance
    triads = list (sorted (triads.items (), key=itemgetter (1), reverse=True))
    if args.triadLimit > 0:
        triads = triads[:args.triadLimit]

    # map layer+button combinations, because a layer may have multiple modifier
    # keys (→ can’t use ButtonCombination)
    keys = []
    values = []
    for i, l in enumerate (layout.layers):
        # get all available keys from the keyboard instead the layout, so
        # currently unused keys are considered as well
        for k in keyboard.keys ():
            # ignore buttons that are not letter keys for now. Also do not
            # mutate modifier key positions.
            # XXX: only works for single-button-modifier
            if not isinstance (k, LetterButton) or layout.isModifier (frozenset ([k])):
                logging.info (f'ignoring {k}')
                continue
            keys.append ((i, k))
            values.append ((i, k))
    buttonMap = dict (zip (keys, values))

    pins = [(x, keyboard[y] if y else None) for x, y in args.pin]

    opt = LayoutOptimizer (buttonMap, triads, layout, pins, writer)
    if args.randomize:
        logging.info ('randomizing initial layout')
        for i in range (len (buttonMap)*2):
            opt.mutate (withEnergy=False)
    try:
        state, relEnergy = opt.run (steps=args.steps)
        energy = opt.energy ()
        optimalButtonMap = state.buttonMap
    except KeyboardInterrupt:
        logging.info ('interrupted')
        return 1

    # plausibility checks: 1:1 mapping for every button
    assert set (optimalButtonMap.keys ()) == set (optimalButtonMap.values ())
    opt._resetEnergy ()
    expectEnergy = opt.energy ()
    # there may be some error due to floating point semantics
    assert abs (expectEnergy - energy) < 0.0001, (expectEnergy, energy)

    layers = [Layer (modifier=[], layout=dict ()) for l in layout.layers]
    for i, l in enumerate (layout.layers):
        for m in l.modifier:
            layers[i].modifier.append ([k.name for k in m])
        for k, v in l.layout.items ():
            try:
                (newLayer, newK) = optimalButtonMap[(i, k)]
            except KeyError:
                # not found, probably not used and thus not mapped
                print ('key', i, k, 'not in mapping table, assuming id()', file=sys.stderr)
                layers[i].layout[k.name] = v
            else:
                assert newK not in layers[newLayer].layout
                layers[newLayer].layout[newK.name] = v

    newLayout = GenericLayout (f'{layout.name}-new', layers)
    print (f'# steps: {args.steps}\n# keyboard: {args.keyboard}\n# layout: {args.layout}\n# triads: {len (triads)}\n# energy: {energy}')
    yaml.dump (newLayout.serialize (), sys.stdout)

    print (f'final energy {energy}', file=sys.stderr)

    return 0

