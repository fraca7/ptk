# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015
# See LICENSE.txt

"""
Simple regular expression engine used by ProgressiveParser.
"""

import six
import re
import collections

#===============================================================================
# Regex objects

class _State(object):
    pass


class DeadState(Exception):
    """
    Raised when the FSA reaches a dead state
    """


class RegularExpression(object):
    """
    Regular expression object (non-deterministic FSA)
    """

    def __init__(self):
        self._transitions = list() # of (startState, class/None, endState)
        self._startState = _State()
        self._finalState = _State()
        self._currentState = None
        self._startStates = set()

    def clone(self):
        """
        Returns a clone of this object. Used by concat() and union()
        so that if you pass several times the same expression states
        don't get all mixed up...
        """
        # pylint: disable=W0212
        result = RegularExpression()
        for startState, trans, endState in self._transitions:
            if startState is self._startState:
                startState = result._startState
            if startState is self._finalState:
                startState = result._finalState
            if endState is self._startState:
                endState = result._startState
            if endState is self._finalState:
                endState = result._finalState
            result._transitions.append((startState, trans, endState))
        result._startStates = set([state for state, _, _ in result._transitions])
        return result

    @staticmethod
    def fromClass(klass):
        """
        Builds a regular expression from a CharacterClass instance
        """
        # pylint: disable=W0212
        result = RegularExpression()
        result._transitions = [(result._startState, klass, result._finalState)]
        result._startStates = set([state for state, _, _ in result._transitions])
        return result

    @staticmethod
    def concat(*rxs):
        """
        Builds the concatenation of several RegularExpression instances
        """
        # pylint: disable=W0212
        rxs = [rx.clone() for rx in rxs]
        result = RegularExpression()
        if rxs:
            result._startState = rxs[0]._startState
            result._transitions = list(rxs[0]._transitions)
            for rx1, rx2 in zip(rxs[:-1], rxs[1:]):
                for startState, trans, endState in rx2._transitions:
                    if startState is rx2._startState:
                        startState = rx1._finalState
                    if endState is rx2._startState:
                        endState = rx1._finalState
                    result._transitions.append((startState, trans, endState))
            result._finalState = rxs[-1]._finalState
        else:
            result._transitions = [(result._startState, None, result._finalState)]
        result._startStates = set([state for state, _, _ in result._transitions])
        return result

    @staticmethod
    def union(*rxs):
        """
        Builds the union of several RegularExpression instances
        """
        # pylint: disable=W0212
        result = RegularExpression()
        for rx in [rx.clone() for rx in rxs]:
            result._transitions.extend(rx._transitions)
            result._transitions.append((result._startState, None, rx._startState))
            result._transitions.append((rx._finalState, None, result._finalState))
        result._startStates = set([state for state, _, _ in result._transitions])
        return result

    @staticmethod
    def kleene(rx):
        """
        Kleene closure
        """
        # pylint: disable=W0212
        result = RegularExpression()
        result._transitions = list(rx._transitions)
        result._transitions.append((result._startState, None, result._finalState))
        result._transitions.append((rx._finalState, None, rx._startState))
        result._transitions.append((result._startState, None, rx._startState))
        result._transitions.append((rx._finalState, None, result._finalState))
        result._startStates = set([state for state, _, _ in result._transitions])
        return result

    @staticmethod
    def exponent(rx, minCount, maxCount=None):
        """
        Arbitrary exponent
        """
        if maxCount is None:
            return RegularExpression.concat(
                RegularExpression.exponent(rx, minCount, minCount),
                RegularExpression.kleene(rx)
                )
        else:
            return RegularExpression.union(*tuple(
                [RegularExpression.concat(*tuple([rx for _ in range(count)])) for count in range(minCount, maxCount+1)]))

    # Matching

    def _epsilonClose(self, states):
        newStates = set(states) # Copy
        while True:
            added = False
            for state in set(newStates):
                for startState, trans, endState in self._transitions:
                    if startState == state and trans is None and endState not in newStates:
                        newStates.add(endState)
                        added = True
            if not added:
                break
        return newStates

    def _closure(self, states, char):
        newStates = set()
        for startState, trans, endState in self._transitions:
            if trans is not None and startState in states and char in trans:
                newStates.add(endState)
        return newStates

    def start(self):
        """
        Resets the internal state to the start state
        """
        self._currentState = self._epsilonClose(set([self._startState]))
        return self

    def feed(self, char):
        """
        Advance the state according to char
        """
        self._currentState = self._epsilonClose(self._closure(self._currentState, char))
        if not self._currentState:
            raise DeadState()
        return self._finalState in self._currentState

    def isDeadEnd(self):
        """
        Checks if the current state is a dead end, i.e. if there are no outgoing transitions from it
        """
        return self._currentState and all([state not in self._startStates for state in self._currentState])

    def match(self, string):
        """
        Match a whole string
        """
        self.start()
        try:
            for char in string:
                self.feed(char)
            return self._finalState in self._currentState
        except DeadState:
            return False

#===============================================================================
# Lexing

class TokenizeError(Exception):
    """Tokenization error in a regular expression"""


class BackslashAtEndOfInputError(TokenizeError):
    """Escape character at end of input"""


class UnterminatedClassError(TokenizeError):
    """Character class not ended"""


class InvalidClassError(TokenizeError):
    """Invalid class, e.g. z-a"""


class InvalidExponentError(TokenizeError):
    """Invalid exponent value"""


class CharacterClass(object): # pylint: disable=R0903
    """Base class for character classes"""

    def __contains__(self, char): # pragma: no cover
        raise NotImplementedError


class AnyCharacterClass(CharacterClass):
    """The ."""

    def __contains__(self, char):
        return char not in [six.u('\n'), six.b('\n')[0]]

    def __eq__(self, other):
        return isinstance(other, AnyCharacterClass)


class RegexCharacterClass(CharacterClass): # pylint: disable=R0903
    """
    Use an actual regex; for character classes
    """

    _cache = dict()

    def __init__(self, pattern):
        if pattern not in self._cache:
            try:
                flags = 0
                if six.PY2 and isinstance(pattern, unicode): # pylint: disable=E0602
                    flags = re.UNICODE
                self._cache[pattern] = re.compile(pattern, flags)
            except re.error as exc:
                raise InvalidClassError(str(exc))
        self._rx = self._cache[pattern]

    def __eq__(self, other): # pragma: no cover
        return self is other # Because of cache

    def __contains__(self, char):
        return self._rx.match(bytes([char]) if six.PY3 and isinstance(char, int) else char) is not None


class LitteralCharacterClass(CharacterClass): # pylint: disable=R0903
    """
    Single char
    """

    def __init__(self, char):
        self._char = char

    def __eq__(self, other):
        return type(self) is type(other) and self._char == other._char # pylint: disable=W0212

    def __contains__(self, char):
        return char == self._char

    def __repr__(self):
        return repr(self._char)


ExponentToken = collections.namedtuple('ExponentToken', ['minCount', 'maxCount'])


class RegexTokenizer(object): # pylint: disable=R0903
    """
    Tokenization of regular expressions. Actually, this does a bit
    more than plain tokenization; it also handles special cases for
    character classes and exponentiation.
    """

    TOK_CLASS = 1
    TOK_EXPONENT = 2
    TOK_LPAREN = 3
    TOK_RPAREN = 4
    TOK_UNION = 5

    Token = collections.namedtuple('Token', ['type', 'value'])

    def __init__(self, regex):
        self._stack = list(reversed(regex))
        self._state = 0
        self._currentClass = None
        self._exponentValue = 0
        self._startExponent = None

        # Six.[ub] behaves badly with strings such as '\\'
        if six.PY2:
            self.ubackslash = '\\'.decode('ascii')
            self.bbackslash = '\\'
        else:
            self.ubackslash = '\\'
            self.bbackslash = '\\'.encode('ascii')

    def tokens(self):
        """
        Returns a list of tokens for the regex passed to the
        constructor. Items are 2-tuples (type, value) where 'type' is
        one of the TOK_* constants.
        """
        tokenList = list()

        while self._stack:
            char = self._stack.pop()
            state = getattr(self, '_state%d' % self._state)
            state = state(char, tokenList)
            self._state = state if state is not None else self._state

        if self._state == 1:
            raise BackslashAtEndOfInputError('Backslash at end of string')
        if 2 <= self._state <= 8:
            raise UnterminatedClassError('Unterminated character class')
        if 9 <= self._state <= 12:
            raise InvalidExponentError('Unterminated {')

        return tokenList

    # "Normal" state

    def _state0(self, char, tokenList):
        # Normal state
        if char in [six.u('*'), six.b('*')[0]]:
            tokenList.append(self.Token(self.TOK_EXPONENT, ExponentToken(0, None)))
        elif char in [six.u('+'), six.b('+')[0]]:
            tokenList.append(self.Token(self.TOK_EXPONENT, ExponentToken(1, None)))
        elif char in [six.u('.'), six.b('.')[0]]:
            tokenList.append(self.Token(self.TOK_CLASS, AnyCharacterClass()))
        elif char in [six.u('('), six.b('(')[0]]:
            tokenList.append(self.Token(self.TOK_LPAREN, char))
        elif char in [six.u(')'), six.b(')')[0]]:
            tokenList.append(self.Token(self.TOK_RPAREN, char))
        elif char in [six.u('|'), six.b('|')[0]]:
            tokenList.append(self.Token(self.TOK_UNION, char))
        elif char == six.u('['):
            self._currentClass = six.StringIO()
            self._currentClass.write(char)
            return 2
        elif char == six.b('[')[0]:
            self._currentClass = six.BytesIO()
            self._currentClass.write(bytes([char]) if six.PY3 else char)
            return 2
        elif char in [six.u('{'), six.b('{')[0]]:
            return 9
        elif char in [six.u(']'), six.b(']')[0], six.u('}'), six.b('}')[0]]:
            raise TokenizeError('Unexpected token "%s"' % char)
        elif char in [self.ubackslash, self.bbackslash]:
            return 1
        else:
            tokenList.append(self.Token(self.TOK_CLASS, LitteralCharacterClass(char)))

    def _state1(self, char, tokenList):
        # After a "\" in normal state
        if char in [six.u('d'), six.u('s'), six.u('w'), six.u('D'), six.u('S'), six.u('W')]:
            tokenList.append(self.Token(self.TOK_CLASS, RegexCharacterClass(self.ubackslash + char)))
        elif char in [six.b('d')[0], six.b('s')[0], six.b('w')[0], six.b('D')[0], six.b('S')[0], six.b('W')[0]]:
            tokenList.append(self.Token(self.TOK_CLASS, RegexCharacterClass(self.bbackslash + char)))
        elif char == six.u('n'):
            tokenList.append(self.Token(self.TOK_CLASS, LitteralCharacterClass(six.u('\n'))))
        elif char == six.u('t'):
            tokenList.append(self.Token(self.TOK_CLASS, LitteralCharacterClass(six.u('\t'))))
        elif char == six.b('n')[0]:
            tokenList.append(self.Token(self.TOK_CLASS, LitteralCharacterClass(six.b('\n')[0])))
        elif char == six.b('t')[0]:
            tokenList.append(self.Token(self.TOK_CLASS, LitteralCharacterClass(six.b('\t')[0])))
        else:
            tokenList.append(self.Token(self.TOK_CLASS, LitteralCharacterClass(char)))
        return 0

    # Character classes

    def _state2(self, char, tokenList):
        # In character class
        if char in [self.ubackslash, self.bbackslash]:
            return 3
        if char in [six.u(']'), six.b(']')[0]]:
            self._currentClass.write(bytes([char]) if six.PY3 and isinstance(char, int) else char)
            tokenList.append(self.Token(self.TOK_CLASS, RegexCharacterClass(self._currentClass.getvalue())))
            self._currentClass = None
            return 0
        self._currentClass.write(bytes([char]) if six.PY3 and isinstance(char, int) else char)

    def _state3(self, char, tokenList): # pylint: disable=W0613
        # After "\" in character class
        if six.PY2 and isinstance(char, str):
            self._currentClass.write(self.bbackslash)
        else:
            self._currentClass.write(self.ubackslash)
        self._currentClass.write(bytes([char]) if six.PY3 and isinstance(char, int) else char)
        return 2

    # Exponent

    def _state9(self, char, tokenList): # pylint: disable=W0613
        # Start of exponent
        if not char.isdigit():
            raise InvalidExponentError('Exponent not starting with a number')
        self._exponentValue = int(char)
        return 10

    def _state10(self, char, tokenList):
        # In exponent, computing start value
        if char in [six.u('-'), six.b('-')[0]]:
            self._startExponent = self._exponentValue
            return 11
        elif char in [six.u('}'), six.b('}')[0]]:
            tokenList.append(self.Token(self.TOK_EXPONENT, ExponentToken(self._exponentValue, self._exponentValue)))
            return 0
        elif char.isdigit():
            self._exponentValue *= 10
            self._exponentValue += int(char)
        else:
            raise InvalidExponentError('Invalid character "%s"' % char)

    def _state11(self, char, tokenList): # pylint: disable=W0613
        # In exponent, expecting second term of interval
        if char in [six.u('}'), six.b('}')[0]]:
            raise InvalidExponentError('Missing range end')
        if not char.isdigit():
            raise InvalidExponentError('Invalid character "%s"' % char)
        self._exponentValue = int(char)
        return 12

    def _state12(self, char, tokenList):
        # In exponent, computing end value
        if char in [six.u('}'), six.b('}')[0]]:
            if self._startExponent > self._exponentValue:
                raise InvalidExponentError('Invalid exponent range %d-%d' % (self._startExponent, self._exponentValue))
            tokenList.append(self.Token(self.TOK_EXPONENT, ExponentToken(self._startExponent, self._exponentValue)))
            return 0
        if not char.isdigit():
            raise InvalidExponentError('Invalid character "%s"' % char)
        self._exponentValue *= 10
        self._exponentValue += int(char)

#===============================================================================
# Parsing

class RegexParseError(Exception):
    """
    Regular expression parse error
    """


class RegexParser(object):
    """
    Actual parsing of regular expression strings
    """

    def parse(self, tokens):
        """
        Well, duh
        """
        tokens = list(tokens)
        expr, pos = self._parse_E1(tokens, 0)
        if len(tokens) != pos:
            raise RegexParseError('Unexpected token "%s"' % tokens[pos].value)
        return expr

    def _parse_E1(self, tokens, pos):
        expr, pos = self._parse_E2(tokens, pos)
        return self._parse_R1(expr, tokens, pos)

    def _parse_R1(self, left, tokens, pos):
        while pos != len(tokens) and tokens[pos].type == RegexTokenizer.TOK_UNION:
            expr, pos = self._parse_E2(tokens, pos + 1)
            left = self.union(left, expr)
        return left, pos

    def _parse_E2(self, tokens, pos):
        expr, pos = self._parse_E3(tokens, pos)
        return self._parse_R2(expr, tokens, pos)

    def _parse_R2(self, left, tokens, pos):
        while True:
            try:
                tempExpr, tempPos = self._parse_E3(tokens, pos)
                self._parse_R2(tempExpr, tokens, tempPos)
            except RegexParseError:
                break
            expr, pos = self._parse_E3(tokens, pos)
            left = self.concat(left, expr)
        return left, pos

    def _parse_E3(self, tokens, pos):
        expr, pos = self._parse_E(tokens, pos)
        return self._parse_R3(expr, tokens, pos)

    def _parse_R3(self, left, tokens, pos):
        while pos != len(tokens) and tokens[pos].type == RegexTokenizer.TOK_EXPONENT:
            left = self.exponent(left, tokens[pos].value)
            pos += 1
        return left, pos

    def _parse_E(self, tokens, pos):
        if pos == len(tokens):
            raise RegexParseError('Expected "(" or letter')
        if tokens[pos].type == RegexTokenizer.TOK_LPAREN:
            expr, pos = self._parse_E1(tokens, pos + 1)
            if pos == len(tokens) or tokens[pos].type != RegexTokenizer.TOK_RPAREN:
                raise RegexParseError('Missing ")"')
            return expr, pos + 1
        elif tokens[pos].type == RegexTokenizer.TOK_CLASS:
            return self.klass(tokens[pos].value), pos + 1
        raise RegexParseError('Unexpected token "%s"' % tokens[pos].value)

    # Delegate

    def union(self, rx1, rx2): # pylint: disable=C0111,R0201
        return RegularExpression.union(rx1, rx2)

    def concat(self, rx1, rx2): # pylint: disable=C0111,R0201
        return RegularExpression.concat(rx1, rx2)

    def exponent(self, rx, exp): # pylint: disable=C0111,R0201
        return RegularExpression.exponent(rx, exp.minCount, exp.maxCount)

    def klass(self, charClass): # pylint: disable=C0111,R0201
        return RegularExpression.fromClass(charClass)


def buildRegex(rx):
    """
    Shortcut to build a RegularExpression object from a string
    """
    return RegexParser().parse(RegexTokenizer(rx).tokens())
