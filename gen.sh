#!/bin/bash
# Generate build.ninja that builds the docs/stats/…

corpusdir=corpus
layouts="ar-lulua ar-asmo663 ar-linux ar-malas ar-phonetic ar-osman ar-khorshid ar-osx ar-idlebi ar-alramly ar-ergoarabic ar-qtaish"
layoutsXmodmap="ar-lulua"
corpora="`ls ${corpusdir}`"

cat <<EOF
### auto-generated by gen.sh. Do not edit. ###

### settings ###
builddir=_build
reportdir=_build/report
tempdir=_build/_temp
statsdir=_build/_stats
datadir=lulua/data
corpusdir=${corpusdir}
wikiextractor=3rdparty/wikiextractor/WikiExtractor.py
osmconvert=3rdparty/osmctools/src/osmconvert
fontdir=3rdparty/plex/IBM-Plex-Sans-Arabic/fonts/complete/woff2/
optrounds=100000
# pin layers, keep hand-optimized numbers, keep top row free
optpins=0;1;2;0,B*;3,*
optmodel=mod01

### pools ###
# lulua-write uses internal parallelization and should not be run more than
# once concurrently. It also uses alot of memory, so…
pool write
    depth = 1

### rules ###
rule opt
    command = lulua-optimize -n \$optrounds -r -p \$optpins -l ar-lulua -m \$optmodel < \$in > \$out

rule render-svg
    command = lulua-render -l \$layout svg \$out

rule render-svg-print
    command = lulua-render -l \$layout svg -s lulua/data/render-svg-print.css \$out

rule svg2pdf
    command = rsvg-convert -f pdf \$in > \$out

rule render-svg-heat
    command = lulua-render -l \$layout svg --heatmap=\$in \$out

rule render-xmodmap
    command = lulua-render -l \$layout xmodmap \$out

rule analyze-heat
    command = lulua-analyze -l \$layout keyheatmap < \$in > \$out

rule write-bbcarabic
    command = find \$in | lulua-write \$layout file brotli tar bbcarabic | lulua-analyze combine > \$out
    pool = write

rule write-aljazeera
    command = find \$in | lulua-write \$layout file brotli tar aljazeera | lulua-analyze combine > \$out
    pool = write

rule write-epub
    command = find \$in | lulua-write \$layout epub | lulua-analyze combine > \$out
    pool = write

rule write-tanzil
    command = find \$in | lulua-write \$layout file text | lulua-analyze combine > \$out
    pool = write

rule write-tei2
    command = find \$in | lulua-write \$layout file brotli tar xml tei2 | lulua-analyze combine > \$out
    pool = write

rule write-opensubtitles
    command = find \$in | lulua-write \$layout file brotli tar xml opensubtitles | lulua-analyze combine > \$out
    pool = write

rule write-arwiki
    command = \$wikiextractor -ns 0 --json -o - \$in 2>/dev/null | jq .text | lulua-write \$layout json | lulua-analyze combine > \$out
    pool = write

rule write-osm
    command = \$osmconvert --csv='name:ar' \$in | sort -u | lulua-write \$layout lines | lulua-analyze combine > \$out
    pool = write

rule combine
    command = cat \$in | lulua-analyze combine > \$out

rule mkdir
    command = mkdir -p \$out

rule letterfreq
    command = lulua-analyze -l ar-lulua letterfreq < \$in > \$out

rule analyze-layoutstats
    command = lulua-analyze -l \$layout layoutstats < \$in > \$out

rule analyze-corpusstats
    command = lulua-analyze -l ar-lulua corpusstats \$metadata < \$stats > \$out

rule wordlist
    command = lulua-analyze -l ar-lulua latinime < \$in > \$out

rule analyze-triadeffortdata
    command = lulua-analyze -l \$layout triadeffortdata < \$in > \$out

rule analyze-triadeffortplot
    command = cat \$in | lulua-analyze -l ar-lulua triadeffortplot > \$out

rule report
    command = lulua-report -c \$corpus -l \$layoutstats > \$out

rule cp
    command = cp \$in \$out

rule gz
    command = gzip -c \$in > \$out

rule configure-make
    command = cd \$in && autoreconf --install && ./configure && make

rule zipR
    command = ./makezip.sh \$in \$out

rule render-winkbd
    command = lulua-render -l ar-lulua winkbd \$out

rule render-klavaro
    command = lulua-render -l ar-lulua klavaro \$out

rule ninjaC
    command = ninja -C \$dir

### build targets ###
build \$reportdir: mkdir
build \$reportdir/fonts: mkdir
build \$tempdir: mkdir
build \$reportdir/letterfreq.json: letterfreq \$statsdir/ar-lulua/all.pickle || \$reportdir
build \$reportdir/style.css: cp \$datadir/report/style.css || \$reportdir
build \$reportdir/lulua-logo.svg: cp \$datadir/report/lulua-logo.svg || \$reportdir
# wordlist
build \$tempdir/lulua.combined: wordlist \$statsdir/ar-lulua/all.pickle || \$tempdir
build \$reportdir/lulua.combined.gz: gz \$tempdir/lulua.combined || \$reportdir


build \$reportdir/fonts/IBMPlexSansArabic-Regular.woff2: cp \$fontdir/IBMPlexSansArabic-Regular.woff2 || \$reportdir/fonts
build \$reportdir/fonts/IBMPlexSansArabic-Thin.woff2: cp \$fontdir/IBMPlexSansArabic-Thin.woff2 || \$reportdir/fonts

# build osmconvert
build \$osmconvert: configure-make 3rdparty/osmctools

# Klavaro keyboard
build \$reportdir/lulua_ar.kbd: render-klavaro || \$reportdir
    layout = ${l}

# windows drivers
build \$tempdir/winkbd: mkdir lulua/data/winkbd
EOF
# Create dependencies for the non-customized files
for f in $(ls lulua/data/winkbd/); do
    echo "build \$tempdir/winkbd/$f: cp lulua/data/winkbd/$f || \$tempdir/winkbd"
    w64infiles+=" \$tempdir/winkbd/$f"
done
w64infiles+=" \$tempdir/winkbd/keyboard.c"
cat <<EOF
build \$tempdir/winkbd/keyboard.c: render-winkbd || \$tempdir/winkbd
build \$tempdir/ar-lulua-w64: mkdir
build \$tempdir/winkbd/System32/kbdarlulua.dll \$tempdir/winkbd/SysWOW64/kbdarlulua.dll: ninjaC | $w64infiles
    dir = \$tempdir/winkbd
EOF

w64zipfile="System32/kbdarlulua.dll SysWOW64/kbdarlulua.dll README.txt lulua.reg install.bat"
deps=""
for f in $w64zipfile; do
	echo "build \$tempdir/ar-lulua-w64/$f: cp \$tempdir/winkbd/$f || \$tempdir/ar-lulua-w64"
	deps+=" \$tempdir/ar-lulua-w64/$f"
done
cat <<EOF
build \$reportdir/ar-lulua-w64.zip: zipR \$tempdir/ar-lulua-w64 | $deps

EOF

bbcarabicfiles=`find $corpusdir/bbcarabic/ -type f -name '*.tar.br' | tr '\n' ' '`
aljazeerafiles=`find $corpusdir/aljazeera/ -type f -name '*.tar.br' | tr '\n' ' '`
unfiles=`find $corpusdir/un-v1.0-tei/ -type f -name '*.tar.br' | tr '\n' ' '`
opensubtitlesfiles=`find $corpusdir/opensubtitles-2018/ -type f -name '*.tar.br' | tr '\n' ' '`
hindawifiles=`find $corpusdir/hindawi/ -type f -name '*.epub' | tr '\n' ' '`

# targets for every layout
for l in $layouts; do
cat <<EOF
build \$statsdir/${l}: mkdir

build \$statsdir/${l}/bbcarabic.pickle: write-bbcarabic $bbcarabicfiles || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/aljazeera.pickle: write-aljazeera $aljazeerafiles || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/hindawi.pickle: write-epub $hindawifiles || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/tanzil-quaran.pickle: write-tanzil \$corpusdir/tanzil-quaran/plain.txt || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/arwiki.pickle: write-arwiki \$corpusdir/arwiki/arwiki-20190701-pages-articles.xml.bz2 || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/osm.pickle: write-osm \$corpusdir/osm/planet-191104.osm.pbf || \$statsdir/${l} \$osmconvert
    layout = ${l}

build \$statsdir/${l}/un-v1.0-tei.pickle: write-tei2 $unfiles || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/opensubtitles-2018.pickle: write-opensubtitles $opensubtitlesfiles || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/all.pickle: combine \$statsdir/${l}/bbcarabic.pickle \$statsdir/${l}/aljazeera.pickle \$statsdir/${l}/tanzil-quaran.pickle \$statsdir/${l}/arwiki.pickle \$statsdir/${l}/osm.pickle \$statsdir/${l}/hindawi.pickle \$statsdir/${l}/un-v1.0-tei.pickle \$statsdir/${l}/opensubtitles-2018.pickle || \$statsdir/${l}

build \$reportdir/${l}.svg: render-svg || \$reportdir
    layout = ${l}

build \$tempdir/${l}-heat.yaml: analyze-heat \$statsdir/${l}/all.pickle || \$tempdir
    layout = ${l}

build \$tempdir/${l}-triadeffort.pickle: analyze-triadeffortdata \$statsdir/${l}/all.pickle || \$tempdir
    layout = ${l}

build \$reportdir/${l}-heat.svg: render-svg-heat \$tempdir/${l}-heat.yaml || \$reportdir
    layout = ${l}

build \$tempdir/${l}-print.svg: render-svg-print || \$tempdir
    layout = ${l}

build \$reportdir/${l}.pdf: svg2pdf \$tempdir/${l}-print.svg || \$reportdir

build \$tempdir/${l}-layoutstats.pickle: analyze-layoutstats \$statsdir/${l}/all.pickle || \$tempdir
    layout = ${l}

EOF
# included by index.html and thus must be its dependencies
layoutstatsfiles+=" \$tempdir/${l}-layoutstats.pickle"
done

# layouts with xmodmap support
for l in $layoutsXmodmap; do
cat <<EOF
build \$reportdir/${l}.xmodmap: render-xmodmap || \$reportdir
    layout = ${l}

EOF
done

# statistics for each corpus (ar-lulua) and html rendering
metafiles=""
for c in $corpora; do
cat <<EOF
build \$tempdir/metadata-$c.yaml: analyze-corpusstats \$statsdir/ar-lulua/$c.pickle \$corpusdir/$c/metadata.yaml || \$tempdir \$corpusdir/$c/metadata.yaml
    metadata = \$corpusdir/$c/metadata.yaml
    stats = \$statsdir/ar-lulua/$c.pickle

EOF
metafiles+=" \$tempdir/metadata-$c.yaml"
done

echo -n "build \$reportdir/triadeffort.json: analyze-triadeffortplot "
for l in $layouts; do
    echo -n "\$tempdir/${l}-triadeffort.pickle "
done
echo "|| \$reportdir"

# dependencies are not properly modeled, always rebuild
cat <<EOF
build always: phony
build \$reportdir/index.html: report | always || \$reportdir $metafiles $layoutstatsfiles
    corpus = $metafiles
    layoutstats = $layoutstatsfiles
EOF

