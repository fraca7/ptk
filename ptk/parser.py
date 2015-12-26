# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015
# See LICENSE.txt

import six
import functools
import collections
import logging
import re

from ptk.lexer import ProgressiveLexer, EOF, token
# production is only imported so that client code doesn't have to import it from grammar
from ptk.grammar import Grammar, Production, GrammarError, production
from ptk.utils import Singleton


class ParseError(Exception):
    """
    Syntax error when parsing.

    :ivar token: The unexpected token.
    """
    def __init__(self, grammar, tok, state):
        self.token = tok
        super(ParseError, self).__init__(six.u('Unexpected token "%s" in state "%s"') % (tok.value, sorted(state)))

        self._expecting = set()
        for terminal in grammar.tokenTypes():
            if grammar.__actions__.get((state, terminal), None) is not None:
                self._expecting.add(terminal)

    def expecting(self):
        """
        Returns a set of tokens types that would have been valid in input.
        """
        return self._expecting


def leftAssoc(*operators):
    """
    Class decorator for left associative operators. Use this to
    decorate your :py:class:`Parser` class. Operators passed as
    argument are assumed to have the same priority. The later you
    declare associativity, the higher the priority; so the following
    code

    .. code-block:: python

       @leftAssoc('+', '-')
       @leftAssoc('*', '/')
       class MyParser(LRParser):
           # ...

    declares '+' and '-' to be left associative, with the same
    priority. '*' and '/' are also left associative, with a higher
    priority than '+' and '-'.

    See also the *priority* argument to :py:func:`production`.
    """
    def _wrapper(cls):
        cls.__precedence__.insert(0, ('left', set(operators)))
        return cls
    return _wrapper


def rightAssoc(*operators):
    """
    Class decorator for right associative operators. Same remarks as :py:func:`leftAssoc`.
    """
    def _wrapper(cls):
        cls.__precedence__.insert(0, ('right', set(operators)))
        return cls
    return _wrapper


def nonAssoc(*operators):
    """
    Class decorator for non associative operators. Same remarks as :py:func:`leftAssoc`.
    """
    def _wrapper(cls):
        cls.__precedence__.insert(0, ('non', set(operators)))
        return cls
    return _wrapper


class _StartState(six.with_metaclass(Singleton, object)):
    __reprval__ = six.u('\u03A3') if six.PY3 else six.u('(START)')


class _ResolveError(Exception):
    pass


@functools.total_ordering
class _Item(object):
    def __init__(self, prod, dot, terminal):
        self.production = prod
        self.dot = dot
        self.terminal = terminal

    def shouldReduce(self):
        """
        Returns True if the dot is in last position
        """
        return self.dot == len(self.production.right)

    def next(self):
        """
        Returns an item with the dot advanced one position
        """
        return _Item(self.production, self.dot + 1, self.terminal)

    def __repr__(self):
        symbols = list(self.production.right)
        symbols.insert(self.dot, six.u('\u2022') if six.PY3 else six.u('.'))
        return six.u('%s -> %s (%s)') % (self.production.name, six.u(' ').join(symbols), self.terminal)

    def __eq__(self, other):
        return (self.production, self.dot, self.terminal) == (other.production, other.dot, other.terminal)

    def __lt__(self, other):
        return (self.production, self.dot, self.terminal) < (other.production, other.dot, other.terminal)

    def __hash__(self):
        return hash((self.production, self.dot, self.terminal))


class _Accept(BaseException):
    def __init__(self, result):
        self.result = result
        super(_Accept, self).__init__()


_StackItem = collections.namedtuple('_StackItem', ['state', 'value'])


class _Shift(object):
    def __init__(self, newState):
        self.newState = newState

    def doAction(self, grammar, stack, tok): # pylint: disable=W0613
        """Shifts"""
        stack.append(_StackItem(self.newState, tok.value))
        return True


class _Reduce(object):
    def __init__(self, item):
        self.item = item
        self.nargs = len(item.production.right)

    def doAction(self, grammar, stack, tok): # pylint: disable=W0613
        """Reduces"""
        if self.nargs:
            args = [stackItem.value for stackItem in stack[-self.nargs:]]
            stack[-self.nargs:] = []
            prodVal = self.item.production.apply(grammar, args)
        else:
            prodVal = self.item.production.apply(grammar, [])
        stack.append(_StackItem(grammar.goto(stack[-1].state, self.item.production.name), prodVal))
        return False


class LRParser(Grammar):
    """
    LR(1) parser. This class is intended to be used with a lexer class
    derived from :py:class:`LexerBase`, using inheritance; it
    overrides :py:func:`LexerBase.newToken` so you must inherit from
    the parser first, then the lexer:

    .. code-block:: python

       class MyParser(LRParser, ReLexer):
           # ...

    """
    def __init__(self): # pylint: disable=R0914,R0912
        super(LRParser, self).__init__()
        self.__restartParser()

    def newToken(self, tok):
        while True:
            action = self.__actions__.get((self.__stack[-1].state, tok.type), None)
            if action is None:
                raise ParseError(self, tok, self.__stack[-1].state)

            try:
                if action.doAction(self, self.__stack, tok):
                    break
            except _Accept as exc:
                self.__restartParser()
                self.newSentence(exc.result)
                break

    def newSentence(self, sentence): # pragma: no cover
        """
        This is called when the start symbol has been reduced.

        :param sentence: The value associated with the start symbol.
        """
        raise NotImplementedError

    @classmethod
    def prepare(cls):
        for prod in cls.productions():
            if prod.name is _StartState:
                break
        else:
            def acceptor(grammar, result):
                raise _Accept(result)
            prod = Production(_StartState, acceptor)
            prod.addSymbol(cls._defaultStartSymbol() if cls.startSymbol is None else cls.startSymbol, name='result')
            cls.__productions__.insert(0, prod)

        cls.startSymbol = _StartState
        super(LRParser, cls).prepare()

        # Compute go_to and states
        allSyms = cls.tokenTypes() | cls.nonterminals()
        goto = dict()
        cls._startState = frozenset([_Item(prod, 0, EOF)])
        states = set([cls._startState])
        stack = [cls._startState]
        while stack:
            state = stack.pop()
            stateClosure = cls.__itemSetClosure(state)
            for symbol in allSyms:
                # Compute goto(symbol, state)
                nextState = set()
                for item in stateClosure:
                    if not item.shouldReduce() and item.production.right[item.dot] == symbol:
                        nextState.add(item.next())
                if nextState:
                    nextState = frozenset(nextState)
                    goto[(state, symbol)] = nextState
                    if nextState not in states:
                        states.add(nextState)
                        stack.append(nextState)

        # Compute actions
        logger = logging.getLogger('LRParser')
        cls.__actions__ = dict()
        reachable = set()
        for state in states:
            for item in cls.__itemSetClosure(state):
                if item.shouldReduce():
                    action = _Reduce(item)
                    reachable.add(item.production.name)
                    cls.__addReduceAction(state, item.terminal, action)
                else:
                    symbol = item.production.right[item.dot]
                    if symbol in cls.tokenTypes():
                        cls.__addShiftAction(state, symbol, _Shift(goto[(state, symbol)]))

        cls.__resolveConflicts(logger)

        usedTokens = set([symbol for state, symbol in cls.__actions__.keys() if symbol is not EOF])
        if usedTokens != cls.tokenTypes():
            logger.warning('The following tokens are not used: %s', ','.join(sorted(cls.tokenTypes() - usedTokens)))

        if reachable != cls.nonterminals():
            logger.warning('The following nonterminals are not reachable: %s', ','.join(sorted(cls.nonterminals() - reachable)))

        # Reductions only need goto entries for nonterminals
        cls._goto = dict([((state, symbol), newState) for (state, symbol), newState in goto.items() if symbol not in cls.tokenTypes()])

        parts = list()
        if cls.nSR:
            parts.append('%d shift/reduce conflicts' % cls.nSR)
        if cls.nRR:
            parts.append('%d reduce/reduce conflicts' % cls.nRR)
        if parts:
            logger.warning(', '.join(parts))

        # Cast to tuple because sets are not totally ordered
        for index, state in enumerate([tuple(cls._startState)] + sorted([tuple(state) for state in states if state != cls._startState])):
            logger.debug('State %d', index)
            for item in sorted(state):
                logger.debug('    %s', item)
        logger.info('%d states.', len(states))

    @classmethod
    def __shouldPreferShift(cls, logger, reduceAction, symbol):
        logger.info('Shift/reduce conflict for "%s" on "%s"', reduceAction.item, symbol)

        prodPrecedence = reduceAction.item.production.precedence(cls)
        tokenPrecedence = cls.terminalPrecedence(symbol)

        # If both precedences are specified, use priority/associativity
        if prodPrecedence is not None and tokenPrecedence is not None:
            prodAssoc, prodPrio = prodPrecedence
            tokenAssoc, tokenPrio = tokenPrecedence
            if prodPrio > tokenPrio:
                logger.info('Resolving in favor of reduction because of priority')
                return False
            if prodPrio < tokenPrio:
                logger.info('Resolving in favor of shift because of priority')
                return True
            if prodAssoc == tokenAssoc:
                if prodAssoc == 'non':
                    logger.info('Resolving in favor of error because of associativity')
                    raise _ResolveError()
                if prodAssoc == 'left':
                    logger.info('Resolving in favor of reduction because of associativity')
                    return False
                logger.info('Resolving in favor of shift because of associativity')
                return True

        # At least one of those is not specified; use shift
        logger.warning('Could not disambiguate shift/reduce conflict for "%s" on "%s"; using shift' % (reduceAction.item, symbol))
        cls.nSR += 1
        return True

    @classmethod
    def __resolveConflicts(cls, logger):
        cls.nSR = 0
        cls.nRR = 0

        for (state, symbol), actions in sorted(cls.__actions__.items()):
            action = actions.pop()
            while actions:
                conflicting = actions.pop()
                try:
                    action = cls.__resolveConflict(logger, action, conflicting, symbol)
                except _ResolveError:
                    del cls.__actions__[(state, symbol)]
                    break
            else:
                cls.__actions__[(state, symbol)] = action

    @classmethod
    def __resolveConflict(cls, logger, action1, action2, symbol):
        if isinstance(action2, _Shift):
            action1, action2 = action2, action1

        if isinstance(action1, _Shift):
            # Shift/reduce
            return action1 if cls.__shouldPreferShift(logger, action2, symbol) else action2

        # Reduce/reduce
        logger.warning('Reduce/reduce conflict between "%s" and "%s"', action1.item, action2.item)
        cls.nRR += 1

        # Use the first one to be declared
        for prod in cls.productions():
            if prod == action1.item.production:
                logger.warning('Using "%s', prod)
                return action1
            if prod == action2.item.production:
                logger.warning('Using "%s', prod)
                return action2

    @classmethod
    def __addReduceAction(cls, state, symbol, action):
        cls.__actions__.setdefault((state, symbol), list()).append(action)

    @classmethod
    def __addShiftAction(cls, state, symbol, action):
        for existing in cls.__actions__.get((state, symbol), list()):
            if isinstance(existing, _Shift):
                return
        cls.__actions__.setdefault((state, symbol), list()).append(action)

    @classmethod
    def goto(cls, state, symbol):
        return cls._goto[(state, symbol)]

    def __restartParser(self):
        self.__stack = [_StackItem(self._startState, None)]

    @classmethod
    def __itemSetClosure(cls, items):
        result = set(items)
        while True:
            prev = set(result)
            for item in [item for item in result if not item.shouldReduce()]:
                symbol = item.production.right[item.dot]
                if symbol not in cls.tokenTypes():
                    terminals = cls.first(*tuple(item.production.right[item.dot + 1:] + [item.terminal]))
                    for prod in (prod for prod in cls.productions() if prod.name == symbol):
                        for terminal in terminals:
                            result.add(_Item(prod, 0, terminal))
            if prev == result:
                break
        return result


class ProductionParser(LRParser, ProgressiveLexer): # pylint: disable=R0904
    # pylint: disable=C0111,C0103,R0201
    def __init__(self, callback, priority, grammarClass): # pylint: disable=R0915
        self.callback = callback
        self.priority = priority
        self.grammarClass = grammarClass

        super(ProductionParser, self).__init__()

    @classmethod
    def prepare(cls, **kwargs):
        # Obviously cannot use @production here

        # DECL -> identifier "->" PRODS
        prod = Production('DECL', cls.DECL)
        prod.addSymbol('identifier', 'name')
        prod.addSymbol('arrow')
        prod.addSymbol('PRODS', 'prods')
        cls.__productions__.append(prod)

        # PRODS -> P
        prod = Production('PRODS', cls.PRODS1)
        prod.addSymbol('P', 'prod')
        cls.__productions__.append(prod)

        # PRODS -> PRODS "|" P
        prod = Production('PRODS', cls.PRODS2)
        prod.addSymbol('PRODS', 'prods')
        prod.addSymbol('union')
        prod.addSymbol('P', 'prod')
        cls.__productions__.append(prod)

        # P -> P SYM
        prod = Production('P', cls.P1)
        prod.addSymbol('P', 'prod')
        prod.addSymbol('SYM', 'sym')
        cls.__productions__.append(prod)

        # P -> ɛ
        prod = Production('P', cls.P2)
        cls.__productions__.append(prod)

        # SYM -> SYMNAME PROPERTIES
        prod = Production('SYM', cls.SYM)
        prod.addSymbol('SYMNAME', 'symname')
        prod.addSymbol('PROPERTIES', 'properties')
        cls.__productions__.append(prod)

        # SYMNAME -> identifier
        prod = Production('SYMNAME', cls.SYMNAME1)
        prod.addSymbol('identifier', 'identifier')
        cls.__productions__.append(prod)

        # SYMNAME -> litteral
        prod = Production('SYMNAME', cls.SYMNAME2)
        prod.addSymbol('litteral', 'litteral')
        cls.__productions__.append(prod)

        # PROPERTIES -> ɛ
        prod = Production('PROPERTIES', cls.PROPERTIES1)
        cls.__productions__.append(prod)

        # PROPERTIES -> lchev identifier rchev
        prod = Production('PROPERTIES', cls.PROPERTIES2)
        prod.addSymbol('lchev')
        prod.addSymbol('identifier', 'name')
        prod.addSymbol('rchev')
        cls.__productions__.append(prod)

        super(ProductionParser, cls).prepare(**kwargs)

    def newSentence(self, startSymbol):
        name, prods = startSymbol
        if name in self.grammarClass.tokenTypes():
            raise GrammarError('"%s" is a token name and cannot be used as non-terminal' % name)

        for prod in prods:
            prod.name = name
        self.grammarClass.__productions__.extend(prods)

    # Lexer

    @staticmethod
    def ignore(char):
        return char in ' \t\n'

    @token('->')
    def arrow(self, tok):
        pass

    @token('<')
    def lchev(self, tok):
        pass

    @token('>')
    def rchev(self, tok):
        pass

    @token(r'\|')
    def union(self, tok):
        pass

    @token('[a-zA-Z_][a-zA-Z0-9_]*')
    def identifier(self, tok):
        pass

    @token(r'"|\'')
    def litteral(self, tok):
        class StringBuilder(object):
            def __init__(self, quotetype):
                self.quotetype = quotetype
                self.chars = list()
                self.state = 0
            def feed(self, char):
                if self.state == 0:
                    if char == '\\':
                        self.state = 1
                    elif char == self.quotetype:
                        return 'litteral', ''.join(self.chars)
                    else:
                        self.chars.append(char)
                elif self.state == 1:
                    self.chars.append(char)
                    self.state = 0
        self.setConsumer(StringBuilder(tok.value))

    # Parser

    def DECL(self, name, prods):
        return (name, prods)

    def PRODS1(self, prod):
        return [prod]

    def PRODS2(self, prods, prod):
        prods.append(prod)
        return prods

    def P1(self, sym, prod):
        symbol, properties = sym
        prod.addSymbol(symbol, name=properties.get('name', None))
        return prod

    def P2(self):
        # 'name' is replaced in newSentence()
        return Production(None, self.callback, priority=self.priority)

    def SYMNAME1(self, identifier):
        return identifier

    def SYMNAME2(self, litteral):
        name = litteral
        if name not in self.grammarClass.tokenTypes():
            self.grammarClass.addTokenType(name, lambda s, tok: None, re.escape(name), None)
        return name

    def SYM(self, symname, properties):
        return (symname, properties)

    def PROPERTIES1(self):
        return dict()

    def PROPERTIES2(self, name):
        return dict(name=name)
