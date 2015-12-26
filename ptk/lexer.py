# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015
# See LICENSE.txt

import six
import inspect
import re
import collections

from ptk.regex import buildRegex, DeadState, RegexTokenizer
from ptk.utils import Singleton


# In Python 3 we'd use __prepare__ and a multi-valued ordered dict...
_TOKREGISTER = list()


class _LexerMeta(type):
    def __new__(metacls, name, bases, attrs):
        global _TOKREGISTER # pylint: disable=W0603
        try:
            attrs['__tokens__'] = (set(), list()) # Set of token names, list of (rx, callback, defaultType)
            klass = super(_LexerMeta, metacls).__new__(metacls, name, bases, attrs)
            for func, rx, toktypes in _TOKREGISTER:
                klass.addTokenType(func.__name__, func, rx, toktypes)
            return klass
        finally:
            _TOKREGISTER = list()


def token(rx, types=None):
    def _wrap(func):
        _TOKREGISTER.append((func, rx, types))
        return func
    return _wrap


class LexerError(Exception):
    """
    Unrecognized token in input

    :ivar lineno: Line in input
    :ivar colno: Column in input
    """
    def __init__(self, char, colno, lineno):
        super(LexerError, self).__init__('Unrecognized token "%s" at line %d, column %d' % (char, lineno, colno))
        self.lineno = lineno
        self.colno = colno


class EOF(six.with_metaclass(Singleton, object)):
    """
    End symbol
    """

    __reprval__ = six.u('$')

    @property
    def type(self):
        """Read-only attribute for Token duck-typing"""
        return self
    @property
    def value(self):
        """Read-only attribute for Token duck-typing"""
        return self


_LexerPosition = collections.namedtuple('_LexerPosition', ['column', 'line'])


class LexerBase(six.with_metaclass(_LexerMeta, object)):
    """
    This defines the interface for lexer classes. For concrete
    implementations, see :py:class:`ProgressiveLexer` and
    :py:class:`ReLexer`.
    """

    Token = RegexTokenizer.Token

    # Shut up pychecker. Those are actually set by the metaclass.
    __tokens__ = ()

    class _MutableToken(object):
        def __init__(self, type_, value):
            self.type = type_
            self.value = value

        def token(self):
            """Returns the unmutable equivalent"""
            return EOF if EOF in [self.type, self.value] else RegexTokenizer.Token(self.type, self.value)

    def __init__(self):
        super(LexerBase, self).__init__()
        self.restartLexer()

    def restartLexer(self, resetPos=True):
        if resetPos:
            self.__pos = _LexerPosition(0, 1)
        self.__consumer = None

    def position(self):
        """
        :return: The current position in stream as a 2-tuple (column, line).
        """
        return self.__pos

    def advanceColumn(self, count=1):
        """
        Advances the current position by *count* columns.
        """
        col, row = self.__pos
        self.__pos = _LexerPosition(col + count, row)

    def advanceLine(self, count=1):
        """
        Advances the current position by *count* lines.
        """
        _, row = self.__pos
        self.__pos = _LexerPosition(0, row + count)

    @staticmethod
    def ignore(char):
        """
        Override this to ignore characters in input stream. The
        default is to ignore spaces and tabs.

        :param char: The character to test
        :return: True if *char* should be ignored
        """
        return char in [six.b(' '), six.u(' '), six.b('\t'), six.u('\t')]

    def setConsumer(self, consumer):
        """
        Sets the current consumer. A consumer is an object with a
        *feed* method; all characters seen on the input stream after
        the consumer is set are passed directly to it. When the *feed*
        method returns a 2-tuple (type, value), the corresponding
        token is generated and the consumer reset to None. This may be
        handy to parse tokens that are not easily recognized by a
        regular expression but easily by code; for instance the
        following lexer recognizes C strings without having to use
        negative lookahead:

        .. code-block:: python

           class MyLexer(ReLexer):
               @token('"')
               def cstring(self, tok):
                   class CString(object):
                       def __init__(self):
                           self.state = 0
                           self.value = StringIO.StringIO()
                       def feed(self, char):
                           if self.state == 0:
                               if char == '"':
                                   return 'cstring', self.value.getvalue()
                               if char == '\\\\':
                                   self.state = 1
                               else:
                                   self.value.write(char)
                           elif self.state == 1:
                               self.value.write(char)
                               self.state = 0
                   self.setConsumer(CString())
        """
        self.__consumer = consumer

    def consumer(self):
        return self.__consumer

    def parse(self, string): # pragma: no cover
        """
        Parses the whole *string*
        """
        raise NotImplementedError

    def newToken(self, tok): # pragma: no cover
        """
        This method will be invoked as soon as a token is recognized on input.

        :param tok: The token. This is a named tuple with *type* and *value* attributes.
        """
        raise NotImplementedError

    @classmethod
    def addTokenType(cls, name, callback, regex, types=None):
        for typeName in [name] if types is None else types:
            if typeName is not EOF:
                cls.__tokens__[0].add(typeName)
        cls.__tokens__[1].append((regex, callback, name if types is None else None))

    @classmethod
    def _allTokens(cls):
        tokens = (set(), list())
        for base in inspect.getmro(cls):
            if issubclass(base, LexerBase):
                tokens[0].update(base.__tokens__[0])
                tokens[1].extend(base.__tokens__[1])
        return tokens

    @classmethod
    def tokenTypes(cls):
        """
        :return: the set of all token names, as strings.
        """
        return cls._allTokens()[0]


class ReLexer(LexerBase): # pylint: disable=W0223
    """
    Concrete lexer based on Python regular expressions. this is
    **way** faster than :py:class:`ProgressiveLexer` but it can only
    tokenize whole strings.
    """
    def __init__(self):
        self.__regexes = list()
        for rx, callback, defaultType in self._allTokens()[1]:
            if six.PY2 and isinstance(rx, str) or six.PY3 and isinstance(rx, bytes):
                crx = re.compile(six.b('^') + rx)
            else:
                crx = re.compile(six.u('^') + rx)
            self.__regexes.append((crx, callback, defaultType))
        super(ReLexer, self).__init__()

    def parse(self, string):
        pos = 0
        while pos < len(string):
            char = string[pos]
            if char == '\n':
                self.advanceLine()
            else:
                self.advanceColumn()
            if self.consumer() is None:
                if self.ignore(char):
                    pos += 1
                    continue
                self.__findMatch(string, pos)
            else:
                tok = self.consumer().feed(char)
                if tok is not None:
                    self.setConsumer(None)
                    if tok[0] is not None:
                        self.newToken(self.Token(*tok))
                pos += 1
        self.newToken(EOF)

    def __findMatch(self, string, pos):
        match = None
        matchlen = 0
        for rx, callback, defaultType in self.__regexes:
            mtc = rx.search(string[pos:])
            if mtc:
                value = mtc.group(0)
                if len(value) > matchlen:
                    match = value, callback, defaultType
                    matchlen = len(value)

        if match:
            value, callback, defaultType = match
            tok = self._MutableToken(defaultType, value)
            callback(self, tok)
            pos += matchlen
            if self.consumer() is None and tok.type is not None:
                self.newToken(tok.token())
        else:
            raise LexerError(string[pos:pos+10], *self.position())


class ProgressiveLexer(LexerBase): # pylint: disable=W0223
    """
    Concrete lexer based on a simple pure-Python regular expression
    engine. This lexer is able to tokenize an input stream in a
    progressive fashion; just call the
    :py:func:`ProgressiveLexer.feed` method with whatever bytes are
    available when they're available. Useful for asynchronous
    contexts.

    This is **slow as hell**.
    """
    def restartLexer(self, resetPos=True):
        self.__currentState = [(buildRegex(rx).start(), callback, defaultType, [0]) for rx, callback, defaultType in self._allTokens()[1]]
        self.__currentMatch = list()
        self.__matches = list()
        self.__maxPos = 0
        self.__state = 0
        super(ProgressiveLexer, self).restartLexer(resetPos=resetPos)

    def parse(self, string):
        if six.PY3 and isinstance(string, bytes):
            string = [chr(c).encode('ascii') for c in string]
        for char in string:
            self.feed(char)
        self.feed(EOF)

    def feed(self, char, charPos=None): # pylint: disable=R0912,R0915
        """
        Handle a single input character. When you're finished, call
        this with EOF as argument.
        """

        if char == '\n':
            self.advanceLine()
        else:
            self.advanceColumn()

        if self.consumer() is not None:
            tok = self.consumer().feed(char)
            if tok is not None:
                self.setConsumer(None)
                if tok[0] is not None:
                    self.newToken(self.Token(*tok))
            return

        try:
            if char is EOF:
                if self.__state == 0:
                    self.restartLexer()
                    self.newToken(EOF)
                    return
                self.__maxPos = max(self.__maxPos, max(pos[0] for regex, callback, defaultType, pos in self.__currentState))
                if self.__maxPos == 0 and self.__currentMatch:
                    raise LexerError(self.__currentMatch[0][0], *self.__currentMatch[0][1])
                self.__matches.extend([(pos[0], callback) for regex, callback, defaultType, pos in self.__currentState if pos[0] == self.__maxPos])
                self.__matches = [(pos, callback) for pos, callback in self.__matches if pos == self.__maxPos]
            else:
                if self.__state == 0 and self.ignore(char):
                    return
                self.__state = 1

                newState = list()
                for regex, callback, defaultType, pos in self.__currentState:
                    try:
                        if regex.feed(char):
                            pos[0] = len(self.__currentMatch) + 1
                    except DeadState:
                        if pos[0]:
                            self.__matches.append((pos[0], callback))
                            self.__maxPos = max(self.__maxPos, pos[0])
                    else:
                        newState.append((regex, callback, defaultType, pos))

                if all([regex.isDeadEnd() for regex, callback, defaultType, pos in newState]):
                    for regex, callback, defaultType, pos in newState:
                        self.__matches.append((len(self.__currentMatch) + 1, callback))
                        self.__maxPos = max(self.__maxPos, len(self.__currentMatch) + 1)
                    newState = list()

                self.__matches = [(pos, callback) for pos, callback in self.__matches if pos == self.__maxPos]
                self.__currentState = newState

                self.__currentMatch.append((char, self.position() if charPos is None else charPos))
                if self.__currentState:
                    return

                if self.__maxPos == 0:
                    raise LexerError(char, *self.position())
        except LexerError:
            self.restartLexer()
            raise

        self.__finalizeMatch()

        if char is EOF:
            self.restartLexer()
            self.newToken(EOF)

    def __finalizeMatch(self):
        # First declared token method
        matches = set([callback for _, callback in self.__matches])
        match = type(self.__currentMatch[0][0])().join([char for char, pos in self.__currentMatch[:self.__maxPos]]) # byte or unicode
        remain = self.__currentMatch[self.__maxPos:]
        self.restartLexer(False)
        for _, callback, defaultType in self._allTokens()[1]:
            if callback in matches:
                tok = self._MutableToken(defaultType, match)
                callback(self, tok)
                if tok.type is None or self.consumer() is not None:
                    break
                self.newToken(tok.token())
                break
        for char, pos in remain:
            self.feed(char, charPos=pos)
