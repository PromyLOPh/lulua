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

