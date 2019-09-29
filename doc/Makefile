### settings ###
CORPUSDIR:=../corpus
STATSDIR:=..
WIKIEXTRACTOR:=../3rdparty/wikiextractor/WikiExtractor.py
OPTROUNDS=100000
# pin layers, keep hand-optimized numbers, keep top row free
OPTPINS='0;1;2;0,Bl1;0,Bl2;0,Bl3;0,Bl4;0,Bl5;0,Bl6;0,Bl7;0,Br6;0,Br5;0,Br4;0,Br3;0,Br2;0,Br1;3,Cl4;3,Cl3;3,Cl2;3,Cl1;3,Dl4;3,Dl3;3,Dl2;3,Dl1;3,El5;3,El4;3,El3;3,El2;3,Dl5;3,Cl5;3,El6'
OPTMODEL=mod01

all: ar-lulua.xmodmap ar-lulua.svg ar-asmo663.svg ar-linux.svg ar-malas.svg ar-phonetic.svg ar-osman.svg letterfreq.json ar-khorshid.svg

letterfreq.json: ../stats.pickle
	lulua-analyze -l ar-lulua letterfreq < $< > $@

ar-lulua.xmodmap:
	lulua-render xmodmap -l ar-lulua $@

ar-lulua.svg:
	lulua-render svg -l ar-lulua $@

ar-asmo663.svg:
	lulua-render svg -l ar-asmo663 $@

ar-linux.svg:
	lulua-render svg -l ar-linux $@

ar-malas.svg:
	lulua-render svg -l ar-malas $@

ar-phonetic.svg:
	lulua-render svg -l ar-phonetic $@

ar-osman.svg:
	lulua-render svg -l ar-osman $@

ar-khorshid.svg:
	lulua-render svg -l ar-khorshid $@

### corpora to stats ###
# Sorry, but I can’t provide corpus data due to copyright issues
$(STATSDIR)/stats-bbcarabic.pickle: $(CORPUSDIR)/bbcarabic/raw
	time find $< -type f | lulua-write bbcarabic ar-lulua > $@

$(STATSDIR)/stats-aljazeera.pickle: $(CORPUSDIR)/aljazeera/raw
	time find $< -type f | lulua-write aljazeera ar-lulua > $@

$(STATSDIR)/stats-tanzil.pickle: $(CORPUSDIR)/tanzil-quaran/plain.txt.lz
	echo $< | lulua-write text ar-lulua | lulua-combine-stats > $@

$(STATSDIR)/stats-arwiki.pickle: $(CORPUSDIR)/arwiki/arwiki-20190701-pages-articles.xml.bz2
	$(WIKIEXTRACTOR) -ns 0 --json -o - $< 2>/dev/null | jq .text | lulua-write json ar-lulua | lulua-combine-stats > $@

$(STATSDIR)/stats.pickle: $(STATSDIR)/stats-arwiki.pickle \
		$(STATSDIR)/stats-tanzil.pickle $(STATSDIR)/stats-aljazeera.pickle \
		$(STATSDIR)/stats-bbcarabic.pickle
	cat $^ | lulua-combine-stats > $@

### optimization ###
optimized.yaml: $(STATSDIR)/stats.pickle
	lulua-optimize -n $(OPTROUNDS) -r -p $(OPTPINS) -l ar-lulua -m $(OPTMODEL) < $< > $@

