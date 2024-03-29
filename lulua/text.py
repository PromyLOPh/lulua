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

import sys, argparse, pickle, json, logging, xml.dom.minidom, queue
from io import StringIO, BytesIO
from functools import partial
from itertools import chain
from multiprocessing import Process, Queue, cpu_count, current_process
from subprocess import Popen, PIPE

from tqdm import tqdm
import ebooklib
from ebooklib import epub
import html5lib
from html5lib.filters.base import Filter
import brotli

from .keyboard import defaultKeyboards
from .layout import defaultLayouts
from .writer import Writer

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
                yield html5lib.constants.entities[key]
            else:
                assert False

class BrotliFile:
    __slots__ = ('decompressor', 'readchunk', 'fd', 'buf')

    def __init__ (self, fd, readchunk=100*1024):
        self.fd = fd
        self.readchunk = readchunk
        self.decompressor = brotli.Decompressor ()
        self.buf = b''

    def __enter__ (self):
        return self

    def __exit__ (self, exc_type, exc_val, exc_tb):
        return True

    def read (self, num=None):
        while not self.decompressor.is_finished ():
            if num is not None and len (self.buf) >= num:
                break
            self.buf += self.decompressor.process (self.fd.read (self.readchunk))
        if num is not None:
            b = self.buf[0:num]
            self.buf = self.buf[num:]
        else:
            b = self.buf
            self.buf = b''
        return b

    def seekable (self):
        return False

    def close (self):
        self.decompressor = None

def filterTar (fd):
    # Python’s tarfile module is painfully slow. We can do better.
    pos = 0
    blocksize = 512
    emptyblock = b'\0'*blocksize

    while True:
        # read header
        header = fd.read (blocksize)
        pos += blocksize
        if header == b'' or header == emptyblock:
            break
        assert header[256:256+8] == b'\0ustar  ', (header[256:256+8])
        size = int (header[124:124+12].rstrip (b'\0'), base=8)

        # read body
        if size > 0:
            yield BytesIO (fd.read (size))
            pos += size

        # align to next 512 byte block
        into = pos%blocksize
        if into != 0:
            pad = blocksize-into
            fd.read (pad)
            pos += pad

def filterBrotli (fd):
    yield BrotliFile (fd)

def filterHtml (selectFunc, fd):
    document = html5lib.parse (fd)
    walker = html5lib.getTreeWalker("etree")
    stream = walker (document)
    s = HTMLSerializer()
    yield ''.join (s.serialize(Select (stream, selectFunc)))

def filterEpub (item):
    """ epub reader """
    book = epub.read_epub (item.rstrip ())
    logging.debug (f'reading ebook {item}')
    for item in book.get_items_of_type (ebooklib.ITEM_DOCUMENT):
        logging.debug (f'got item {item.get_name ()}')
        # XXX: in theory html5lib should be able to detect the encoding of
        # bytes(), but it does not.
        document = html5lib.parse (item.get_content ().decode ('utf-8'))
        walker = html5lib.getTreeWalker("etree")
        stream = walker (document)
        s = HTMLSerializer()
        yield ''.join (s.serialize (stream))
    # It looks like ebooklib is leaking ZipFile instances somewhere, which
    # can be prevented by resetting the book before the GC grabs it.
    book.reset ()
    del book

def filterText (fd):
    yield fd.read ().decode ('utf-8')

def filterLines (item):
    """ Read items (i.e. lines) as is """
    yield item

def filterJson (item):
    yield json.loads (item)

def filterFile (item):
    with open (item.rstrip (), 'rb') as fd:
        yield fd

def filterXml (fd):
    try:
        yield xml.dom.minidom.parse (fd)
    except Exception:
        logging.error (f'invalid xml document {fd}')

def getText (nodelist):
    """ Helper to retrieve text from an XML node list """
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def filterTEI2 (doc):
    """ TEI.2 format used for United Nations parallel corpus """
    out = []
    for text in doc.getElementsByTagName ('text'):
        for body in text.getElementsByTagName ('body'):
            for p in body.getElementsByTagName ('p'):
                for s in p.getElementsByTagName ('s'):
                    out.append (getText (s.childNodes))
                out.append ('')
    yield '\n'.join (out)

def filterOpenSubtitles (doc):
    """
    XML-based format used by the (raw!) OpenSubtitles dump found here:
    http://opus.nlpl.eu/OpenSubtitles-v2018.php
    """

    out = []
    for s in doc.getElementsByTagName ('s'):
        # strip newlines, which are mostly unintentional due to
        # pretty-printed xml structure
        out.append (getText (s.childNodes).strip ())
    yield '\n'.join (out)

def filterMediawikiMarkdown (text):
    """
    Convert mediawiki to markdown
    """
    p = subprocess.Popen (['pandoc', '-f', 'mediawiki', '-t', 'markdown'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.stdin.write (text.encode ('utf-8'))
    p.stdin.close ()
    text = p.stdout.read ().decode ('utf-8')
    ret = p.wait ()
    # make sure we’re not leaking fd’s
    p.stdout.close ()
    del p
    if ret != 0:
        logging.error ('pandoc rejected document')
    else:
        yield text

f = dict(
    aljazeera=lambda x: x['name'] == 'div' and x['data'].get ((None, 'id')) == 'DynamicContentContainer',
    bbcarabic=lambda x: x['name'] == 'div' and x['data'].get ((None, 'property')) == 'articleBody',
    )

filterAvail = dict(
    aljazeera=partial(filterHtml, f['aljazeera']),
    bbcarabic=partial(filterHtml, f['bbcarabic']),
    text=filterText,
    json=filterJson,
    epub=filterEpub,
    tei2=filterTEI2,
    opensubtitles=filterOpenSubtitles,
    lines=filterLines,
    xml=filterXml,
    file=filterFile,
    tar=filterTar,
    mediawikimarkdown=filterMediawikiMarkdown,
    brotli=filterBrotli,
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
    'ﻹ': 'لإ',
    'ﻷ': 'لأ',
    # nbsp
    '\u00a0': ' ',
    }

def mapChars (text, m):
    """ For all characters in text, replace if found in map m or keep as-is """
    return ''.join (map (lambda x: m.get (x, x), text))

def apply (fs, items):
    """ Apply the first function fs[0] to all items, flatten the result and repeat """
    if not fs:
        return items
    else:
        return apply (fs[1:], chain.from_iterable (map (fs[0], items)))

from .stats import allStats, makeCombined

def writeWorker (layout, funcs, inq, outq, statusq, benchmark):
    try:
        keyboard = defaultKeyboards['ibmpc105']
        combined = makeCombined (keyboard)
        itemsProcessed = 0

        while True:
            item = inq.get ()
            if item is None:
                break

            # extract (can be multiple texts per item)
            i = 0
            for text in apply (funcs, [item]):
                if benchmark:
                    i += 1
                    continue

                # map chars; make sure we’re using unix line endings, which is
                # only one character
                text = mapChars (text, charMap).replace ('\r\n', '\n')

                logging.debug (text)

                # init a new writer for every item
                w = Writer (layout)
                # stats
                stats = [cls(w) for cls in allStats]
                for match, event in w.type (StringIO (text)):
                    for s in stats:
                        s.process (event)

                for s in stats:
                    combined[s.name].update (s)

                i += 1
            # only update ocasionally, this is an expensive operation
            statusq.put (i)
            itemsProcessed += i
        if itemsProcessed > 0:
            outq.put (combined)
        else:
            outq.put (None)
    except Exception as e:
        # async exceptions
        outq.put (e)

def statusWorker (statusq):
    with tqdm (unit='item', smoothing=0) as bar:
        while True:
            try:
                num = statusq.get (block=True, timeout=1)
                if num is None:
                    break
                bar.update (n=num)
            except queue.Empty:
                bar.update (n=0)

def write ():
    """ Extract corpus source file, convert to plain text, map chars and create stats """

    parser = argparse.ArgumentParser(description='Import text and create stats.')
    parser.add_argument('--benchmark', action='store_true', help='Benchmark filter, no stats')
    parser.add_argument('-j', '--jobs', metavar='NUM',
            default=cpu_count (), type=int, help='Number of parallel jobs')
    parser.add_argument('-k', '--keyboard', metavar='KEYBOARD',
            default='ibmpc105', help='Physical keyboard name')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable debugging output')
    parser.add_argument('layout', metavar='LAYOUT', help='Keyboard layout name')
    parser.add_argument('filter', metavar='FILTER', choices=filterAvail.keys(), nargs='+', help='Data filter')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig (level=logging.DEBUG)
    else:
        logging.basicConfig (level=logging.INFO)

    keyboard = defaultKeyboards[args.keyboard]
    layout = defaultLayouts[args.layout].specialize (keyboard)
    filterSel = [filterAvail[x] for x in args.filter]

    # limit queue sizes to limit memory usage
    inq = Queue (args.jobs*2)
    outq = Queue (args.jobs+1)
    statusq = Queue (args.jobs+1)

    logging.info (f'using {args.jobs} workers')
    workers = []
    for i in range (args.jobs):
        p = Process(target=writeWorker,
                args=(layout, filterSel, inq, outq, statusq, args.benchmark),
                daemon=True,
                name=f'worker-{i}')
        p.start()
        workers.append (p)

    statusp = Process(target=statusWorker,
            args=(statusq,),
            daemon=True,
            name=f'status')
    statusp.start()

    try:
        for l in sys.stdin:
            inq.put (l)

            # something is wrong
            if not outq.empty ():
                break
    except KeyboardInterrupt:
        pass

    # exit workers
    # every one of them will consume exactly one item and write one in return
    for w in workers:
        inq.put (None)
        item = outq.get ()
        if isinstance (item, Exception):
            raise item
        if item is not None:
            pickle.dump (item, sys.stdout.buffer, pickle.HIGHEST_PROTOCOL)
    assert outq.empty ()

    statusq.put (None)
    statusp.join ()

    # and then we can kill them
    for w in workers:
        w.join ()

    return 0

import bz2, sys, json, subprocess
from xml.etree.ElementTree import iterparse
def extractMediawiki ():
    parser = argparse.ArgumentParser(description='Extract raw wikitext from mediawiki dump.')
    parser.add_argument('file', metavar='FILE', help='bzip2-compressed dump')
    args = parser.parse_args()

    with bz2.open (args.file, 'r') as fd:
        for event, elem in iterparse (fd, ['start', 'end']):
            if event == 'end' and elem.tag == '{http://www.mediawiki.org/xml/export-0.10/}text':
                text = ''.join (elem.itertext ())
                json.dump (text, sys.stdout, ensure_ascii=False)
                sys.stdout.write ('\n')

