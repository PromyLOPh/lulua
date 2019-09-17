all: ar-lulua.xmodmap ar-lulua.svg

#letterfreq.json: ../stats.pickle
#	lulua-plot -l ar-lulua letterfreq < $< > $@

ar-lulua.xmodmap:
	lulua-render xmodmap -l ar-lulua $@

ar-lulua.svg:
	lulua-render svg -l ar-lulua $@

