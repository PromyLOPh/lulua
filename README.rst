لؤلؤة
=====

.. image:: https://github.com/PromyLOPh/lulua/workflows/CI/badge.svg

Ergonomic Arabic Keyboard layout. See website_ for details.

.. _website: https://6xq.net/لؤلؤة/

Creating layouts
----------------

Although optimized for the Arabic language it should be possible to create
layouts for other (non-RTL) languages as well. Here’s how to proceed: First,
create a data file ``my-layout.yaml`` that contains all key to character
mappings the new layout should have. Look at ``lulua/data/layouts`` for
examples. Then create statistics for your corpus. For plain-text files use:

.. code:: bash

    cat corpus.txt \
        | lulua-write my-layout.yaml file text \
        | lulua-analyze combine \
        > stats.pickle

Now you can optimize your layout using:

.. code:: bash

    lulua-optimize -n 30000 --triad-limit=30000 -r -l my-layout.yaml \
        < stats.pickle \
        > evolved.yaml

To get a pretty picture (SVG) of your layout render it:

.. code:: bash

   lulua-render -l evolved.yaml svg evolved.svg

It is highly recommended to use `PyPy 3`_ instead of CPython and a powerful
machine with lots of RAM (at least 16 GB).

.. _PyPy 3: http://pypy.org/

Building documentation
----------------------

This essentially means building the website_ and reproducing my results. You’ll
need to obtain the corpora from me_, which are not public due to copyright
issues. Also the following software is required:

- Python/`PyPy 3`_
- Ninja_ (for the build process)
- GNU autotools and a host C compiler (for ``3rdparty/osmctools``)
- GNU bash and zip (for ``makezip.sh``)
- librsvg (``rsvg-convert`` is used to create PDF’s from SVG images)
- MinGW (to compile the Windows keyboard driver)

.. _Ninja: https://ninja-build.org/

Then simply run

.. code:: bash

   ./gen.sh > build.ninja && ninja

to run the analysis and create pretty pictures as well as statistics in
``_build/report``.

.. _me: lars+lulua@6xq.net

Acknowledgements
----------------

This software is using an extended version of carpalx_ by Martin Krzywinski for
optimizing layouts.

.. _carpalx: http://mkweb.bcgsc.ca/carpalx/?typing_effort

