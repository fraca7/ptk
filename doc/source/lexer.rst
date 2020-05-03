
Lexical analysis
================

.. py:decorator:: token(regex, types=None)

   Decorator for token definitions in classes derived from :py:class:`LexerBase`.

   :param str rx: A regular expression defining the possible token values
   :param types: A list of token types that this method can recognize. If omitted, the token type is assumed to be the method's name.
   :type types: List of strings

   Basic usage:

   .. code-block:: python

      from ptk.lexer import ReLexer, token

      class MyLexer(ReLexer):
          @token(r'[a-zA-Z_][a-zA-Z0-9_]*')
          def identifier(self, tok):
              pass

   This will define an *identifier* token type, which value is the
   recognized string. The *tok* parameter holds two attributes,
   *type* and *value*. You can modify the value in place:

   .. code-block:: python

      from ptk.lexer import ReLexer, token

      class MyLexer(ReLexer):
          @token(r'[1-9][0-9]*')
          def number(self, tok):
              tok.value = int(tok.value)

   In some cases it may be necessary to change the token's type as
   well; for instance to disambiguate between identifiers that
   are builtins and other ones. In order for the lexer to know which
   token types can be generated, you should pass a list of strings as the
   *types* parameter:

   .. code-block:: python

      from ptk.lexer import ReLexer, token

      class MyLexer(ReLexer):
          @token(r'[a-zA-Z_][a-zA-Z0-9_]*', types=['builtin', 'identifier'])
          def identifier_or_builtin(self, tok):
              tok.type = 'builtin' if tok.value in ['len', 'id'] else 'identifier'

   In this case the default value of the *type* attribute is *None*
   and you **must** set it. Letting None as token type (or setting it
   to None) will cause the token to be ignored.

   .. note::

      The type of token values depends on the type of the strings
      used to define the regular expressions. Unicode expressions
      will hold Unicode values, and bytes expressions will hold
      bytes values.

   .. note::

      Disambiguation is done the regular way: if several regular
      expressions match the input, the longest match is choosen. If
      the matches are of equal length, the first (in source code
      order) declaration wins.

.. automodule:: ptk.lexer
   :members:
   :member-order: bysource

.. autoclass:: ptk.async_lexer.AsyncLexer

.. py:data:: EOF

   This is a singleton used to indicate end of stream. It may be used
   as a token, a token type and a token value. In the first case it is
   its own type and value.
