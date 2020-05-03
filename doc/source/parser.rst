
Syntactic analysis
==================

.. py:decorator:: production(prod, priority=None)

   Use this decorator to declare a grammar production:

   .. code-block:: python

      from ptk.lexer import ReLexer, token
      from ptk.parser import LRParser, production

      class MyParser(LRParser, ReLexer):
          @production('E -> E "+" E')
	  def sum(self):
	      pass

   See the :ref:`production-syntax` section.

   The *priority* argument may be specified to declare that the production has the same priority as an existing token type. Typical use for unary minus:

   .. code-block:: python

      from ptk.lexer import ReLexer, token
      from ptk.parser import LRParser, production

      class MyParser(LRParser, ReLexer):
          # omitting productions for binary +, -, * and /
	  @production('E -> "-" E', priority='*')
	  def minus(self):
	      pass

   You can also use a token type that has not been declared to the lexer as long as you have declared an explicit priority for it, using one of the associativity decorators:

   .. code-block:: python

      from ptk.lexer import ReLexer, token
      from ptk.parser import LRParser, production, leftAssoc, nonAssoc

      @leftAssoc('+', '-')
      @leftAssoc('*', '/')
      @nonAssoc('UNARYMINUS') # Non associative, higher priority than anything else
      class MyParser(LRParser, ReLexer):
          @production('E -> "-" E', priority='UNARYMINUS')
	  def minus(self):
	      pass

.. automodule:: ptk.parser
   :members:
   :member-order: bysource

.. autoclass:: ptk.async_parser.AsyncLRParser

.. _production-syntax:

Production syntax
-----------------

Basics
^^^^^^

The productions specified through the :py:func:`production` decorator must be specified in a variant of BNF; for example

.. code-block:: python

   from ptk.lexer import ReLexer
   from ptk.parser import LRParser, production

   class Parser(LRParser, ReLexer):
       @production('E -> E plus E')
       def binaryop_sum(self):
           pass

        @production('E -> E minus E')
	def binaryop_minus(self):
	    pass

Here non terminal symbols are uppercase and terminals (token types) are lowercase, but this is only a convention.

When you don't need separate semantic actions you can group several productions by using either the '|' symbol:

.. code-block:: python

   from ptk.lexer import ReLexer
   from ptk.parser import LRParser, production

   class Parser(LRParser, ReLexer):
       @production('E -> E plus E | E minus E')
       def binaryop(self):
           pass

Or decorating the same method several times:

.. code-block:: python

   from ptk.lexer import ReLexer
   from ptk.parser import LRParser, production

   class Parser(LRParser, ReLexer):
       @production('E -> E plus E')
       @production('E -> E minus E')
       def binaryop(self):
           pass

Semantic values
^^^^^^^^^^^^^^^

The semantic value associated with a production is the return value of the decorated method. Values for items on the right side of the production are not passed to the method by default; you have to use a specific syntax to associate each item with a name, which will then be used as the name of a keyword argument passed to the method. The name must be specified between brackets after the item, for instance:

.. code-block:: python

   from ptk.lexer import ReLexer
   from ptk.parser import LRParser, production

   class Parser(LRParser, ReLexer):
       @production('E -> E<left> plus E<right>')
       def sum(self, left, right):
           return left + right

You can thus use  alternatives and default argument values to slightly change the action's behavior depending on the actual matched production:

.. code-block:: python

   from ptk.lexer import ReLexer
   from ptk.parser import LRParser, production

   class Parser(LRParser, ReLexer):
       @production('SYMNAME -> identifier<value> | identifier<value> left_bracket identifier<name> right_bracket')
       def symname(self, value, name=None):
           if name is None:
	       # First form, name not specified
	   else:
	       # Second form

Position in code
^^^^^^^^^^^^^^^^

You may want to store the position in the input stream at which a
production matched, for warning reporting for example. The same syntax
as for the named used in the left part of the production lets you get
this information as a keyword argument:

.. code-block:: python

   from ptk.lexer import ReLexer
   from ptk.parser import LRParser, production

   class Parser(LRParser, ReLexer):
       @production('SYMNAME<position> -> identifier<value> | identifier<value> left_bracket identifier<name> right_bracket')
       def symname(self, position, value, name=None):
           if name is None:
	       # First form, name not specified
	   else:
	       # Second form

In this case, the `position` argument will hold a named 2-tuple with
attributes `column` and `line`. Those start at 1.

Litteral tokens
^^^^^^^^^^^^^^^

A litteral token name may appear in a production, between double quotes. This allows you to skip declaring "simple" tokens at the lexer level.

.. code-block:: python

   from ptk.lexer import ReLexer
   from ptk.parser import LRParser, production

   class Parser(LRParser, ReLexer):
       @production('E -> E "+" E')
       def sum(self):
           pass

.. note::

   Those tokens are considered "declared" after the ones explicitely declared through the :py:func:`token` decorator. This may be important because of the disambiguation rules; see the notes for the :py:func:`token` decorator.

Litteral tokens may be named as well.

Repeat operators
^^^^^^^^^^^^^^^^

A nonterminal in the right side of a production may be immediately
followed by a repeat operator among "*", "+" and "?", which have the
same meaning as in regular expressions. Note that this is only
syntactic sugar; under the hood additional productions are
generated.

.. code-block:: none

   A -> B?

is equivalent to

.. code-block:: none

   A ->
   A -> B

The semantic value is None if the empty production was applied, or the
semantic value of B if the 'A -> B' production was applied.

.. code-block:: none

   A -> B*

is equivalent to

.. code-block:: none

   A ->
   A -> L_B
   L_B -> B
   L_B -> L_B B

The semantic value is a list of semantic values for B. '+' works the
same way except for the empty production, so the list cannot be empty.

Additionally, the '*' and '+' operators may include a separator
specification, which is a symbol name or litteral token between parens:

.. code-block:: none

   A -> B+("|")

is equivalent to

.. code-block:: none

   A -> L_B
   L_B -> B
   L_B -> L_B "|" B

The semantic value is still a list of B values; there is no way to get
the values for the separators.

Wrapping it up
--------------

Fully functional parser for a four-operations integer calculator:

.. code-block:: python

   from ptk.lexer import ReLexer, token
   from ptk.parser import LRParser, production, leftAssoc

   @leftAssoc('+', '-')
   @leftAssoc('*', '/')
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

Parsing lists of integers separated by commas:

.. code-block:: python

   from ptk.lexer import ReLexer, token
   from ptk.parser import LRParser, production

   class Parser(LRParser, ReLexer):
       @token('[1-9][0-9]*')
       def number(self, tok):
           tok.value = int(tok.value)
       @production('LIST -> number*(",")<values>')
       def integer_list(self, values):
           print('Values are: %s' % values)


Conflict resolution rules
=========================

Conflict resolution rules are the same as those used by Yacc/Bison. A shift/reduce conflict is resolved by choosing to shift. A reduce/reduce conflict is resolved by choosing the reduction associated with the first declared production. :py:func:`leftAssoc`, :py:func:`rightAssoc`, :py:func:`nonAssoc` and the *priority* argument to :py:func:`production` allows you to explicitely disambiguate.

Asynchronous lexer/parser
=========================

The :py:class:`AsyncLexer` and :py:class:`AsyncLRParser` classes allow
you to parse an input stream asynchronously. Since this uses the new
asynchronous method syntax introduced in Python 3.5, it's only
available with this version of Python. Additionally, you must install
the `async_generator <https://github.com/python-trio/async_generator>`_ module.

The basic idea is that the production methods are asynchronous. Feed
the input stream one byte/char at a time by awaiting on
:py:func:`AsyncLexer.asyncFeed`. When a token has been recognized
unambiguously, this will in turn await on
:py:func:`AsyncParser.asyncNewToken`. Semantic actions may then be
awaited on as a result.

Note that if you use a consumer in your lexer, the `feed` method must
be asynchronous as well.

The samples directory contains the following example of an
asynchronous parser:

.. code-block:: python

    #!/usr/bin/env python
    # -*- coding: UTF-8 -*-
    
    """
    
    Four operations calculator, asynchronous. Due to various buffering
    problems you probably won't see what's the point unless you force
    stdin to be noninteractive, e.g.
    
    $ echo '3*4+6' | python3 ./async_calc.py
    
    """
    
    import operator, os, asyncio, sys, codecs
    
    from ptk.async_lexer import token, AsyncLexer, EOF
    from ptk.async_parser import production, leftAssoc, AsyncLRParser, ParseError
    
    
    @leftAssoc('+', '-')
    @leftAssoc('*', '/')
    class Parser(AsyncLRParser, AsyncLexer):
        async def asyncNewSentence(self, result):
            print('== Result:', result)
    
        # Lexer
        def ignore(self, char):
            return char in [' ', '\t']
    
        @token(r'[1-9][0-9]*')
        def number(self, tok):
            tok.value = int(tok.value)
    
        # Parser
    
        @production('E -> "-" E<value>', priority='*')
        async def minus(self, value):
            print('== Neg: - %d' % value)
            return -value
    
        @production('E -> "(" E<value> ")"')
        async def paren(self, value):
            return value
    
        @production('E -> number<number>')
        async def litteral(self, number):
            return number
    
        @production('E -> E<left> "+"<op> E<right>')
        @production('E -> E<left> "-"<op> E<right>')
        @production('E -> E<left> "*"<op> E<right>')
        @production('E -> E<left> "/"<op> E<right>')
        async def binaryop(self, left, op, right):
            print('Binary operation: %s %s %s' % (left, op, right))
            return {
                '+': operator.add,
                '-': operator.sub,
                '*': operator.mul,
                '/': operator.floordiv
                }[op](left, right)
    
    
    async def main():
        reader = asyncio.StreamReader()
        await asyncio.get_event_loop().connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
        decoder = codecs.getincrementaldecoder('utf_8')()
    
        parser = Parser()
    
        while True:
            byte = await reader.read(1)
            if not byte:
                break
            char = decoder.decode(byte)
            if char:
                if char == '\n':
                    char = EOF
                else:
                    print('Input char: "%s"' % repr(char))
                await parser.asyncFeed(char)
    
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

Asynchronous lexer/parser using Deferreds
=========================================

The :py:class:`DeferredLexer` and :py:class:`DeferredLRParser` work the same
as :py:class:`AsyncLexer` and :py:class:`AsyncLRParser`, but use
Twisted's Deferred objects instead of Python 3.5-like asynchronous
methods. The special methods are called :py:func:`DeferredLexer.deferNewToken`and
:py:func:`DeferredLRParser.deferNewSentence` and must return
Deferred instances. Semantic actions can return either Deferred
instances or regular values. See the defer_calc.py sample for details.
