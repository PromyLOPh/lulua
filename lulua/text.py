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
Text/corpus handling tools
"""

import sys, argparse, pickle, json, logging
from io import StringIO
from functools import partial
from multiprocessing import Process, Queue, cpu_count, current_process
from subprocess import Popen, PIPE
from tqdm import tqdm

import html5lib
from html5lib.filters.base import Filter

from .keyboard import defaultKeyboards
from .layout import defaultLayouts
from .writer import Writer
from .stats import allStats

def iterchar (fd):
    batchsize = 1*1024*1024
    while True:
        c = fd.read (batchsize)
        if not c:
            break
        yield from c

class Select (Filter):
    def __init__ (self, source, f):
        Filter.__init__ (self, source)
        self.inside = None
        self.f = f

    def __iter__(self):
        isScript = None
        for token in Filter.__iter__(self):
            ttype = token['type']
            if ttype == 'StartTag':
                tname = token['name']
                tdata = token['data']
                if self.f (token):
                    self.inside = 0
                if tname in {'script', 'style'}:
                    isScript = 0

            if isScript is not None:
                if ttype == 'EndTag':
                    isScript -= 1
                    if isScript <= 0:
                        isScript = None
            elif self.inside is not None:
                if ttype == 'StartTag':
                    self.inside += 1
                if ttype == 'EndTag':
                    self.inside -= 1
                if self.inside <= 0:
                    self.inside = None

                yield token

class HTMLSerializer(object):
    def serialize(self, treewalker):
        for token in treewalker:
            type = token["type"]
            if type == "Doctype":
                pass
            elif type == "Characters":
                yield token['data']
            elif type == "SpaceCharacters":
                yield ' '
            elif type in ("StartTag", "EmptyTag"):
                name = token["name"]
                pass
            elif type == "EndTag":
                name = token["name"]
                if name in ('p', 'div'):
                    yield '\n\n'
            elif type == "Comment":
                pass
            elif type == "Entity":
                name = token["name"]
                key = name + ";"
                if key not in html5lib.constants.entities:
                    self.serializeError("Entity %s not recognized" % name)
                yield entities[key]
            else:
                assert False

f = dict(
    aljazeera=lambda x: x['name'] == 'div' and x['data'].get ((None, 'id')) == 'DynamicContentContainer',
    bbcarabic=lambda x: x['name'] == 'div' and x['data'].get ((None, 'property')) == 'articleBody',
    )

class LzipFile:
    __slots__ = ('p', )

    def __init__ (self, path):
        self.p = Popen (['/usr/bin/lzip', '-c', '-d', path], stdout=PIPE)

    def __enter__ (self):
        return self

    def __exit__ (self, exc_type, exc_val, exc_tb):
        self.close ()
        return True

    def read (self, num=None):
        return self.p.stdout.read (num)

    def close (self):
        self.p.wait ()
        assert self.p.returncode == 0

def sourceHtml (selectFunc, item):
    with LzipFile (item.rstrip ()) as fd:
        document = html5lib.parse (fd)
        walker = html5lib.getTreeWalker("etree")
        stream = walker (document)
        s = HTMLSerializer()
        return ''.join (s.serialize(Select (stream, selectFunc)))

def sourceText (item):
    with LzipFile (item.rstrip ()) as fd:
        return fd.read ().decode ('utf-8')

def sourceJson (item):
    return json.loads (item)

sources = dict(
    aljazeera=partial(sourceHtml, f['aljazeera']),
    bbcarabic=partial(sourceHtml, f['bbcarabic']),
    text=sourceText,
    json=sourceJson,
    )

charMap = {
    'ﻻ': 'لا',
    'أ': 'أ',
    'إ': 'إ',
    'ئ': 'ئ',
    'ؤ': 'ؤ',
    ',': '،',
    'آ': 'آ',
    '%': '٪',
    '0': '٠',
    '1': '١',
    '2': '٢',
    '3': '٣',
    '4': '٤',
    '5': '٥',
    '6': '٦',
    '7': '٧',
    '8': '٨',
    '9': '٩',
    '?': '؟',
    ';': '؛',
    # nbsp
    '\u00a0': ' ',
    }

def writeWorker (args, inq, outq):
    keyboard = defaultKeyboards['ibmpc105']
    layout = defaultLayouts['null'].specialize (keyboard)
    w = Writer (layout)
    combined = dict ((cls.name, cls(w)) for cls in allStats)

    while True:
        keyboard = defaultKeyboards[args.keyboard]
        layout = defaultLayouts[args.layout].specialize (keyboard)
        w = Writer (layout)

        item = inq.get ()
        if item is None:
            break

        # extract
        text = sources[args.source] (item)
        text = ''.join (map (lambda x: charMap.get (x, x), text))
        # XXX sanity checks, disable
        for c in charMap.keys ():
            if c in text:
                #print (c, 'is in text', file=sys.stderr)
                assert False, c

        # stats
        stats = [cls(w) for cls in allStats]
        for match, event in w.type (StringIO (text)):
            for s in stats:
                s.process (event)

        for s in stats:
            combined[s.name].update (s)

    outq.put (combined)

def write ():
    """ Extract corpus source file, convert to plain text, map chars and create stats """

    parser = argparse.ArgumentParser(description='Import text and create stats.')
    parser.add_argument('-k', '--keyboard', metavar='KEYBOARD',
            default='ibmpc105', help='Physical keyboard name')
    parser.add_argument('-j', '--jobs', metavar='NUM',
            default=cpu_count (), help='Number of parallel jobs')
    parser.add_argument('source', metavar='SOURCE', choices=sources.keys(), help='Data source extractor name')
    parser.add_argument('layout', metavar='LAYOUT', help='Keyboard layout name')

    args = parser.parse_args()

    logging.basicConfig (level=logging.INFO)

    # limit queue sizes to limit memory usage
    inq = Queue (args.jobs*2)
    outq = Queue (args.jobs+1)

    logging.info (f'using {args.jobs} workers')
    workers = []
    for i in range (args.jobs):
        p = Process(target=writeWorker, args=(args, inq, outq), daemon=True, name=f'worker-{i}')
        p.start()
        workers.append (p)

    try:
        with tqdm (unit='item') as bar:
            for l in sys.stdin:
                inq.put (l)
                bar.update (n=1)
    except KeyboardInterrupt:
        pass

    # exit workers
    # every one of them will consume exactly one item and write one in return
    for w in workers:
        inq.put (None)
        pickle.dump (outq.get (), sys.stdout.buffer, pickle.HIGHEST_PROTOCOL)
    assert outq.empty ()
    # and then we can kill them
    for w in workers:
        w.join ()


