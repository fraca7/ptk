
Parser Toolkit
==============

PTK - (c) Jérôme Laheurte 2015-2019

.. contents:: **Table of contents**

What is PTK ?
-------------

PTK is a LR(1) parser "generator" for Python. It is not actually a
"generator" in the sense that it doesn't output source code, using
Python's dynamic nature to build everything it needs at runtime
instead. Also, it supports asynchronous parsing; see the API
documentation for details.

This code is licensed under the `GNU LGPL version 3 or, at your
option, any later version
<https://www.gnu.org/copyleft/lesser.html>`_.

Why another one of those ?
--------------------------

There are a number of parser generators for Python out there. Most of
them only support LL(1) or PEG. The other ones are either

  - Unmaintained
  - Straight translations from Yacc/Bison, and thus use an ugly syntax
  - All of the above

The main goals of PTK are

  - Clean, compact, Python-friendly syntax
  - Support for asynchronous input streams: why would you need the
    whole input string to start working when the underlying system is
    actually an automaton ?
  - Play nice in 'special' cases, like when the underlying
    'filesystem' is a PyZipFile archive.
  - Don't use hacks like module-level introspection to compensate for
    an ugly design (I'm looking at you PLY). Those tend to produce
    subtle and headache-inducing bugs when running from compiled code.

Supported platforms
-------------------

All unit tests pass on the following platforms/Python version:

+-----+-------+-----+---------+
|     | Linux | OSX | Windows |
+=====+=======+=====+=========+
| 3.3 |       |     |    X    |
+-----+-------+-----+---------+
| 3.4 |       |     |    X    |
+-----+-------+-----+---------+
| 3.5 |       |     |    X    |
+-----+-------+-----+---------+
| 3.6 |   X   |     |    X    |
+-----+-------+-----+---------+
| 3.7 |       |  X  |    X    |
+-----+-------+-----+---------+

Installation
------------

Using pip::

  $ pip install -U ptk

From source::

  $ wget https://pypi.python.org/packages/source/p/ptk/ptk-1.3.6.tar.gz
  $ tar xjf ptk-1.3.6.tar.bz2; cd ptk-1.3.6
  $ sudo python3 ./setup.py install

Sample usage
------------

Four-operations integer calculator:

.. code-block:: python

   from ptk.parser import LRParser, production, leftAssoc
   from ptk.lexer import ReLexer, token
   import operator

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
       expr = input('> ')
       print parser.parse(expr)

Code samples
------------

The *samples* subdirectory in the source tree contains the
aforementioned calculator and a script that generates a skeleton
Python file from a Yacc or Bison grammar file.

API documentation
-----------------

The full documentation is hosted `here <http://ptk.readthedocs.io/en/release-1.3.6/>`_.

Changelog
---------

Version 1.3.6:

- Drop support for Python versions older than 3.3.

Version 1.3.5:

- Update copyright notices
- Fix some packaging issues

Version 1.3.4:

- Added SkipToken for consumers

Version 1.3.3:

- Fix a number of problems when working with bytes in Python 3
- One couldn't mix asynchronous and synchronous parsers in the same program

Version 1.3.2:

- Fix Python regular expression based lexer (use match instead of search)

Version 1.3.1:

- Fix version number in README.rst

Version 1.3.0:

- Added deferred_lexer and deferred_parser (asynchronous parsing using
  Twisted Deferred objects)
- Asynchronous classes cannot be imported from 'regular' modules
  anymore, import them explicitely from 'ptk.async_lexer' and 'ptk.async_parser'.

Version 1.2.0:

- Production methods cannot have the same name any more. This was
  idiotic to begin with. Inheritance thus works as expected.
- Add AsyncLexer and AsyncLRParser for asynchronous parsing.

Version 1.1.0:

- Added repeat operators ('*', '+', '?') in production syntax.
- Support for more yacc/bison declarations in yacc2py sample (most are
  actually ignored)
