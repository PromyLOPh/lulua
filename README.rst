لؤلؤة
=====

Ergonomic Arabic Keyboard layout. See website_ for details.

.. _website: https://6xq.net/لؤلؤة/

Creating layouts
----------------

Although optimized for the Arabic language it should be possible to create
layouts for other (non-RTL) languages as well. Here’s how to proceed: First,
create a data file ``my-layout.yaml`` that contains all key to character
mappings the new layout should have. Look at ``lulua/data/layouts`` for
examples.  Then create statistics for a lzip-compressed corpus of your
choosing:

.. code:: bash

    find corpus/*.txt.lz | lulua-write text my-layout.yaml | lulua-analyze combine > stats.pickle

Now you can optimize your layout using:

.. code:: bash

   lulua-optimize -n 30000 --triad-limit=30000 -r -l my-layout.yaml < stats.pickle > evolved.yaml

To get a pretty picture (SVG) of your layout render it:

.. code:: bash

   lulua-render -l evolved.yaml svg evolved.svg

It is highly recommended to use pypy3_ instead of CPython and a machine with
lots of RAM (at least 16 GB).

.. _pypy3: http://pypy.org/

Building documentation
----------------------

This essentially means building the website_ and reproducing my results. You’ll
need to obtain the corpora from me_, which are not public due to copyright
issues. Then simply run

.. code:: bash

   ./gen.sh > build.ninja && ninja

to analyze them and create pretty pictures as well as statistics in ``doc/``.

.. _me: lars+lulua@6xq.net

Acknowledgements
----------------

This software is using an extended version of carpalx_ by Martin Krzywinski for
optimizing layouts.

.. _carpalx: http://mkweb.bcgsc.ca/carpalx/?typing_effort

