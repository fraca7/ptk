# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015
# See LICENSE.txt

"""
Context-free grammars objects. To define a grammar, inherit the
Grammar class and define a method decorated with 'production' for each
production.
"""

import six
import copy
import functools
import inspect
import logging

from ptk.lexer import EOF, _LexerMeta
from ptk.utils import memoize, Singleton


class Epsilon(six.with_metaclass(Singleton, object)):
    """
    Empty production
    """
    __reprval__ = six.u('\u03B5') if six.PY3 else six.u('(epsilon)')


class GrammarError(Exception):
    """
    Generic grammar error, like duplicate production.
    """


class GrammarParseError(GrammarError):
    """
    Syntax error in a production specification.
    """


@functools.total_ordering
class Production(object):
    """
    Production object
    """
    def __init__(self, name, callback, priority=None):
        self.name = name
        self.callback = callback
        self.right = list()
        self.__priority = priority
        self.__ids = dict() # position => id

    def addSymbol(self, identifier, name=None):
        """
        Append a symbol to the production's right side.
        """
        if name is not None:
            if name in self.__ids.values():
                raise GrammarParseError('Duplicate identifier name "%s"' % name)
            self.__ids[len(self.right)] = name
        self.right.append(identifier)

    def apply(self, grammar, args):
        """
        Invokes the associated callback
        """
        kwargs = dict([(name, args[index]) for index, name in self.__ids.items()])
        return self.callback(grammar, **kwargs)

    def rightmostTerminal(self, grammar):
        """
        Returns the rightmost terminal, or None if there is none
        """
        for symbol in reversed(self.right):
            if symbol in grammar.tokenTypes():
                return symbol

    def precedence(self, grammar):
        """
        Returns the production's priority (specified through the
        'priority' keyword argument to the 'production' decorator), or
        if there is none, the priority for the rightmost terminal.
        """
        if self.__priority is not None:
            return grammar.terminalPrecedence(self.__priority)
        symbol = self.rightmostTerminal(grammar)
        if symbol is not None:
            return grammar.terminalPrecedence(symbol)

    def __eq__(self, other):
        return (self.name, self.right) == (other.name, other.right)

    def __lt__(self, other):
        return (self.name, self.right) < (other.name, other.right)

    def __repr__(self): # pragma: no cover
        return six.u('%s -> %s') % (self.name, six.u(' ').join([repr(p) for p in self.right]) if self.right else repr(Epsilon))

    def __hash__(self):
        return hash((self.name, tuple(self.right)))


# Same remark as in lexer.py.
_PRODREGISTER = list()


class _GrammarMeta(_LexerMeta):
    def __new__(metacls, name, bases, attrs):
        global _PRODREGISTER # pylint: disable=W0603
        try:
            attrs['__productions__'] = list()
            attrs['__precedence__'] = list()
            attrs['__prepared__'] = False
            klass = super(_GrammarMeta, metacls).__new__(metacls, name, bases, attrs)
            for func, string, priority in _PRODREGISTER:
                from ptk.parser import ProductionParser
                parser = ProductionParser(func, priority, klass)
                parser.parse(string)
            return klass
        finally:
            _PRODREGISTER = list()


def production(prod, priority=None):
    def _wrap(func):
        _PRODREGISTER.append((func, prod, priority))
        return func
    return _wrap


class Grammar(six.with_metaclass(_GrammarMeta, object)):
    """
    Base class for a context-free grammar
    """

    __productions__ = list() # Make pylint happy
    __precedence__ = list()
    __prepared__ = False

    startSymbol = None

    def __init__(self):
        # pylint: disable=R0912
        super(Grammar, self).__init__()

        if not self.__prepared__:
            self.prepare()

    @classmethod
    def prepare(cls): # pylint: disable=R0912
        cls.startSymbol = cls._defaultStartSymbol() if cls.startSymbol is None else cls.startSymbol

        productions = set()
        for prod in cls.productions():
            if prod in productions:
                raise GrammarError('Duplicate production "%s"' % prod)
            productions.add(prod)

        allFirsts = dict([(symbol, set([symbol])) for symbol in cls.tokenTypes() | set([EOF])])
        while True:
            prev = copy.deepcopy(allFirsts)
            for nonterminal in cls.nonterminals():
                for prod in cls.productions():
                    if prod.name == nonterminal:
                        if prod.right:
                            for symbol in prod.right:
                                first = allFirsts.get(symbol, set())
                                allFirsts.setdefault(nonterminal, set()).update(first)
                                if Epsilon not in first:
                                    break
                            else:
                                allFirsts.setdefault(nonterminal, set()).add(Epsilon)
                        else:
                            allFirsts.setdefault(nonterminal, set()).add(Epsilon)
            if prev == allFirsts:
                break
        cls.__allFirsts__ = allFirsts

        logger = logging.getLogger('Grammar')
        productions = cls.productions()
        maxWidth = max([len(prod.name) for prod in productions])
        for prod in productions:
            logger.debug('%%- %ds -> %%s' % maxWidth, prod.name, ' '.join(prod.right) if prod.right else Epsilon) # pylint: disable=W1201

        cls.__prepared__ = True

    @classmethod
    def _defaultStartSymbol(cls):
        return cls.productions()[0].name

    @classmethod
    def productions(cls):
        """
        Returns all productions
        """
        productions = list()
        for base in inspect.getmro(cls):
            if issubclass(base, Grammar):
                productions.extend(base.__productions__)
        return productions

    @classmethod
    def nonterminals(cls):
        """
        Return all non-terminal symbols
        """
        result = set()
        for prod in cls.productions():
            result.add(prod.name)
            for symbol in prod.right:
                if symbol not in cls.tokenTypes():
                    result.add(symbol)
        return result

    @classmethod
    def precedences(cls):
        precedences = list()
        for base in inspect.getmro(cls):
            if issubclass(base, Grammar):
                precedences.extend(base.__precedence__)
        return precedences

    @classmethod
    def terminalPrecedence(cls, symbol):
        for index, (associativity, terminals) in enumerate(cls.precedences()):
            if symbol in terminals:
                return associativity, index

    @classmethod
    @memoize
    def first(cls, *symbols):
        """
        Returns the first set for a group of symbols
        """
        first = set()
        for symbol in symbols:
            rfirst = cls.__allFirsts__[symbol]
            first |= set([a for a in rfirst if a is not Epsilon])
            if Epsilon not in rfirst:
                break
        else:
            first.add(Epsilon)
        return first

    @classmethod
    def tokenTypes(cls):
        # Shut up pylint
        return super(Grammar, cls).tokenTypes() # pylint: disable=E1101
