# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015
# See LICENSE.txt

# XXXTODO: when pylint supports async, remove this...
# pylint: skip-file

from ptk.lexer import ProgressiveLexer, token, EOF, LexerError


class AsyncLexer(ProgressiveLexer):
    """

    This class works like :py:class:`ProgressiveLexer` but can be feed
    the input asynchronously via :py:func:`asyncFeed`. It works with
    :py:class:`AsyncLRParser`.

    """

    async def asyncFeed(self, char, charPos=None):
        """
        Asynchronous version of :py:func:`ProgressiveLexer.feed`. This
        awaits on the :py:func:`asyncNewToken` method instead of
        calling 'newToken' synchronously.
        """
        self._input.append((char, charPos))
        while self._input:
            char, charPos = self._input.pop(0)
            for tok in self._feed(char, charPos):
                await self.asyncNewToken(tok)

    async def asyncNewToken(self, tok):
        """
        Asynchronous version of py:func:`LexerBase.newToken`.
        """
        raise NotImplementedError
