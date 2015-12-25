
Parser Toolkit
==============

PTK - (c) Jérôme Laheurte 2015

.. contents:: **Table of contents**

What is PTK ?
-------------

PTK is a LR(1) parser "generator" for Python. It is not actually a
"generator" in the sense that it doesn't output source code, using
Python's dynamic nature to build everything it needs at runtime
instead.

This code is licensed under the `GNU LGPL version 3
<https://www.gnu.org/copyleft/lesser.html>`_.

Supported platforms
-------------------

All unit tests pass on the following platforms/Python version:

+-----+-------+-----+---------+
|     | Linux | OSX | Windows |
+=====+=======+=====+=========+
| 2.7 |   X   |  X  |    X    |
+-----+-------+-----+---------+
| 3.2 |   X   |     |    X    |
+-----+-------+-----+---------+
| 3.3 |       |     |    X    |
+-----+-------+-----+---------+
| 3.4 |       |     |    X    |
+-----+-------+-----+---------+
| 3.5 |       |  X  |         |
+-----+-------+-----+---------+

See the
`Buildbot<https://jeromelaheurte.net/buildbot/ptk/waterfall/>`_ for
details.

Although Python 2.6 is not officially supported, it does work with a
few minor code modifications, namely replacing
functools.total_ordering with the `backport to 2.6<https://pypi.python.org/pypi/total-ordering>`_.

Installation
------------

Using pip::

  $ pip install -U ptk

From source::

  $ wget https://jeromelaheurte.net/ptk/download/ptk-1.0.0.tar.bz2
  $ tar xjf ptk-1.0.0.tar.bz2; cd ptk-1.0.0
  $ sudo python ./setup.py install

Sample usage
------------

Four-operations integer calculator:

.. code-block:: python

   from ptk.parser import LRParser, production, leftAssoc
   from ptk.lexer import ReLexer, token
   import operator, six

   @leftAssoc('+', '-')
   @rightAssoc('*', '/')
   class Parser(LRParser, ReLexer):
       @token('[1-9][0-9]*')
       def number(self, tok):
           tok.value = int(tok.value)
       @production('E -> number<n>')
       def litteral(self, n):
           return n
       @production('E -> "-" E<val>', priority='*')
       def minus(self, val):
           return -val
       @production('E -> "(" E<val> ")"')
       def paren(self, val):
           return val
       @production('E -> E<left> "+"<op> E<right>')
       @production('E -> E<left> "-"<op> E<right>')
       @production('E -> E<left> "*"<op> E<right>')
       @production('E -> E<left> "/"<op> E<right>')
       def binaryop(self, left, op, right):
           return {
	       '+': operator.add,
	       '-': operator.sub,
	       '*': operator.mul,
	       '/': operator.floordiv
	       }[op](left, right)

   parser = Parser()
   while True:
       expr = six.moves.input('> ')
       print parser.parse(expr)

Code samples
------------

The *samples* subdirectory in the source tree contains the
aforementioned calculator and a script that generates a skeleton
Python file from a Yacc or Bison grammar file.
