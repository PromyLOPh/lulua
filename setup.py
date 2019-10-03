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

from setuptools import setup

setup(
    name='lulua',
    version='0.1dev0',
    author='Lars-Dominik Braun',
    author_email='lars+lulua@6xq.net',
    #url='https://6xq.net/crocoite/',
    packages=['lulua'],
    license='LICENSE.txt',
    description='Keyboard layout optimization',
    long_description=open('README.rst').read(),
    long_description_content_type='text/x-rst',
    install_requires=[
        'pygtrie',
        'pyyaml',
        'svgwrite',
        'bokeh',
        'tqdm',
        'html5lib',
        'ebooklib',
    ],
    entry_points={
    'console_scripts': [
            'lulua-analyze = lulua.stats:main',
            'lulua-render = lulua.render:render',
            'lulua-import = lulua.layout:importFrom',
            'lulua-optimize = lulua.optimize:optimize',
            'lulua-write = lulua.text:write',
            ],
    },
    setup_requires=['pytest-runner'],
    tests_require=["pytest", 'pytest-cov'],
    python_requires='>=3.6',
)
