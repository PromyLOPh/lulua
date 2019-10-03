#!/bin/sh
# Generate build.ninja that builds the docs/stats/…

layouts="ar-lulua ar-asmo663 ar-linux ar-malas ar-phonetic ar-osman ar-khorshid"
layoutsXmodmap="ar-lulua"

cat <<EOF
### auto-generated by gen.sh. Do not edit. ###

### settings ###
corpusdir=corpus
statsdir=stats
docdir=doc
wikiextractor=3rdparty/wikiextractor/WikiExtractor.py
optrounds=100000
# pin layers, keep hand-optimized numbers, keep top row free
optpins=0;1;2;0,Bl1;0,Bl2;0,Bl3;0,Bl4;0,Bl5;0,Bl6;0,Bl7;0,Br6;0,Br5;0,Br4;0,Br3;0,Br2;0,Br1;3,Cl4;3,Cl3;3,Cl2;3,Cl1;3,Dl4;3,Dl3;3,Dl2;3,Dl1;3,El5;3,El4;3,El3;3,El2;3,Dl5;3,Cl5;3,El6
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

rule render-svg-heat
    command = lulua-render -l \$layout svg --heatmap=\$in \$out

rule render-xmodmap
    command = lulua-render -l \$layout xmodmap \$out

rule analyze-heat
    command = lulua-analyze -l \$layout keyheatmap < \$in > \$out

rule write-bbcarabic
    command = find \$in -type f | lulua-write bbcarabic \$layout > \$out
    pool = write

rule write-aljazeera
    command = find \$in -type f | lulua-write aljazeera \$layout > \$out
    pool = write

rule write-tanzil
    command = echo \$in | lulua-write text \$layout | lulua-analyze combine > \$out
    pool = write

rule write-arwiki
    command = \$wikiextractor -ns 0 --json -o - \$in 2>/dev/null | jq .text | lulua-write json \$layout | lulua-analyze combine > \$out
    pool = write

rule combine
    command = cat \$in | lulua-analyze combine > \$out

rule mkdir
    command = mkdir -p \$out

rule letterfreq
    command = lulua-analyze -l ar-lulua letterfreq < \$in > \$out

### build targets ###
build \$docdir/letterfreq.json: letterfreq \$statsdir/ar-lulua/all.pickle

EOF

for l in $layouts; do
cat <<EOF
build \$statsdir/${l}: mkdir

build \$statsdir/${l}/bbcarabic.pickle: write-bbcarabic \$corpusdir/bbcarabic/raw || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/aljazeera.pickle: write-aljazeera \$corpusdir/aljazeera/raw || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/tanzil.pickle: write-tanzil \$corpusdir/tanzil-quaran/plain.txt.lz || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/arwiki.pickle: write-arwiki \$corpusdir/arwiki/arwiki-20190701-pages-articles.xml.bz2 || \$statsdir/${l}
    layout = ${l}

build \$statsdir/${l}/all.pickle: combine \$statsdir/${l}/bbcarabic.pickle \$statsdir/${l}/aljazeera.pickle \$statsdir/${l}/tanzil.pickle \$statsdir/${l}/arwiki.pickle || \$statsdir/${l}

build \$docdir/${l}.svg: render-svg
    layout = ${l}

build \$docdir/${l}-heat.yaml: analyze-heat \$statsdir/${l}/all.pickle
    layout = ${l}

build \$docdir/${l}-heat.svg: render-svg-heat \$docdir/${l}-heat.yaml
    layout = ${l}

EOF
done

for l in $layoutsXmodmap; do
cat <<EOF
build \$docdir/${l}.xmodmap: render-xmodmap
    layout = ${l}

EOF
done

