
Syntactic analysis
==================

.. py:decorator:: production(prod, priority=None)

   Use this decorator to declare a grammar production:

   .. code-block:: python

      class MyParser(LRParser, ReLexer):
          @production('E -> E "+" E')
	  def sum(self):
	      pass

   See the :ref:`production-syntax` section.

   The *priority* argument may be specified to declare that the production has the same priority as an existing token type. Typical use for unary minus:

   .. code-block:: python

      class MyParser(LRParser, ReLexer):
          # omitting productions for binary +, -, * and /
	  @production('E -> "-" E', priority='*')
	  def minus(self):
	      pass

   You can also use a token type that has not been declared to the lexer as long as you have declared an explicit priority for it, using one of the associativity decorators:

   .. code-block:: python

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

.. _production-syntax:

Production syntax
-----------------

Basics
^^^^^^

The productions specified through the :py:func:`production` decorator must be specified in a variant of BNF; for example

.. code-block:: python

   class Parser(LRParser, ReLexer):
       @production('E -> E plus E')
       def binaryop(self):
           pass

        @production('E -> E minus E')
	def binaryop(self):
	    pass

Here non terminal symbols are uppercase and terminals (token types) are lowercase, but this is only a convention.

.. note::

   Yes, you can use the same method name for different semantic actions. Don't abuse it.

When you don't need separate semantic actions you can group several productions by using either the '|' symbol:

.. code-block:: python

   class Parser(LRParser, ReLexer):
       @production('E -> E plus E | E minus E')
       def binaryop(self):
           pass

Or decorating the same method several times:

.. code-block:: python

   class Parser(LRParser, ReLexer):
       @production('E -> E plus E')
       @production('E -> E minus E')
       def binaryop(self):
           pass

Semantic values
^^^^^^^^^^^^^^^

The semantic value associated with a production is the return value of the decorated method. Values for items on the right side of the production are not passed to the method by default; you have to use a specific syntax to associate each item with a name, which will then be used as the name of a keyword argument passed to the method. The name must be specified between brackets after the item, for instance:

.. code-block:: python

   class Parser(LRParser, ReLexer):
       @production('E -> E<left> plus E<right>')
       def sum(self, left, right):
           return left + right

You can thus use  alternatives and default argument values to slightly change the action's behavior depending on the actual matched production:

.. code-block:: python

   class Parser(LRParser, ReLexer):
       @production('SYMNAME -> identifier<value> | identifier<value> left_bracket identifier<name> right_bracket')
       def symname(self, value, name=None):
           if name is None:
	       # First form, name not specified
	   else:
	       # Second form

Litteral tokens
^^^^^^^^^^^^^^^

A litteral token name may appear in a production, between double quotes. This allows you to skip declaring "simple" tokens at the lexer level.

.. code-block:: python

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
syntactic sugar; under the hood additional productions are generated:

.. code-block:: none

   A -> B?<name>

is equivalent to

.. code-block:: none

   A -> L_B<name>
   L_B ->
   L_B -> B

The semantic value is None if the empty production was applied, or the
semantic value of B if the 'L_B -> B' production was applied.

.. code-block:: none

   A -> B*<name>

is equivalent to

.. code-block:: none

   A -> L_B<name>
   L_B ->
   L_B -> A
   L_B -> L_B A

The semantic value is a list of semantic values for B. '+' works the
same way except for the empty production, so the list cannot be empty.

Wrapping it up
--------------

Fully functional parser for a four-operations integer calculator:

.. code-block:: python

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

Conflict resolution rules
=========================

Conflict resolution rules are the same as those used by Yacc/Bison. A shift/reduce conflict is resolved by choosing to shift. A reduce/reduce conflict is resolved by choosing the reduction associated with the first declared production. :py:func:`leftAssoc`, :py:func:`rightAssoc`, :py:func:`nonAssoc` and the *priority* argument to :py:func:`production` allows you to explicitely disambiguate.
