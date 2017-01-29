# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015
# See LICENSE.txt

# XXXTODO: when pylint supports async, remove this...
# pylint: skip-file

import six

from ptk.lexer import ProgressiveLexer, token, EOF, LexerError
from ptk.regex import DeadState

try:
    from async_generator import aclosing, async_generator, yield_
except ImportError:
    raise RuntimeError('You need to have the async_generator package installed to use the async lexer.')


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
            async with aclosing(self._asyncFeed(char, charPos)) as agen:
                async for tok in agen:
                    await self.asyncNewToken(tok)

    async def asyncNewToken(self, tok):
        """
        Asynchronous version of py:func:`LexerBase.newToken`.
        """
        raise NotImplementedError

    @async_generator
    async def _asyncFeed(self, char, charPos): # pylint: disable=R0912,R0915
        # Unfortunately this is copy/pasted from ProgressiveLexer._feed to add the async stuff...
        if char in (six.u('\n'), six.b('\n')[0]):
            self.advanceLine()
        else:
            self.advanceColumn()

        if self.consumer() is not None:
            tok = await self.consumer().feed(char)
            if tok is not None:
                self.setConsumer(None)
                if tok[0] is not None:
                    await yield_(self.Token(*tok))
            return

        try:
            if char is EOF:
                if self._state == 0:
                    self.restartLexer()
                    await yield_(EOF)
                    return
                self._maxPos = max(self._maxPos, max(pos[0] for regex, callback, defaultType, pos in self._currentState))
                if self._maxPos == 0 and self._currentMatch:
                    raise LexerError(self._currentMatch[0][0], *self._currentMatch[0][1])
                self._matches.extend([(pos[0], callback) for regex, callback, defaultType, pos in self._currentState if pos[0] == self._maxPos])
                self._matches = [(pos, callback) for pos, callback in self._matches if pos == self._maxPos]
            else:
                if self._state == 0 and self.ignore(char):
                    return
                self._state = 1

                newState = list()
                for regex, callback, defaultType, pos in self._currentState:
                    try:
                        if regex.feed(char):
                            pos[0] = len(self._currentMatch) + 1
                    except DeadState:
                        if pos[0]:
                            self._matches.append((pos[0], callback))
                            self._maxPos = max(self._maxPos, pos[0])
                    else:
                        newState.append((regex, callback, defaultType, pos))

                if all([regex.isDeadEnd() for regex, callback, defaultType, pos in newState]):
                    for regex, callback, defaultType, pos in newState:
                        self._matches.append((len(self._currentMatch) + 1, callback))
                        self._maxPos = max(self._maxPos, len(self._currentMatch) + 1)
                    newState = list()

                self._matches = [(pos, callback) for pos, callback in self._matches if pos == self._maxPos]
                self._currentState = newState

                item = bytes([char]) if six.PY3 and isinstance(char, int) else char
                self._currentMatch.append((item, self.position() if charPos is None else charPos))
                if self._currentState:
                    return

                if self._maxPos == 0:
                    raise LexerError(char, *self.position())
        except LexerError:
            self.restartLexer()
            raise

        tok = self._finalizeMatch()
        if tok is not None:
            await yield_(tok)

        if char is EOF:
            self.restartLexer()
            await yield_(EOF)
