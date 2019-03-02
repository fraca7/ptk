#!/usr/bin/env python3

import base, unittest

from ptk.parser import ParseError, leftAssoc, rightAssoc, nonAssoc
from ptk.deferred_parser import DeferredLRParser
from ptk.lexer import token, EOF
from ptk.deferred_lexer import DeferredLexer
from ptk.grammar import production

from twisted.internet.defer import succeed


# XXXTODO factorize this with test_parser.py


class TestedDeferredParser(DeferredLRParser, DeferredLexer):
    def __init__(self, *args, **kwargs):
        self.seen = list()
        super().__init__(*args, **kwargs)

    @token('[1-9][0-9]*')
    def number(self, tok):
        tok.value = int(tok.value)

    @production('E -> E<left> "+" E<right>')
    def sum(self, left, right):
        self.seen.append(('+', left, right))
        return succeed(left + right)

    @production('E -> E<left> "*" E<right>')
    def mult(self, left, right):
        self.seen.append(('*', left, right))
        return succeed(left * right)

    @production('E -> number<n>')
    def litteral(self, n):
        return succeed(n)

    def deferNewSentence(self, sentence):
        return succeed(None)


class DeferredParserTestCase(unittest.TestCase):
    def parse(self, inputString):
        def realizeDeferred(d):
            self.assertTrue(d.called)
            results = [None, None]
            def success(result):
                results[0] = result
            def error(reason):
                results[1] = reason
            d.addCallback(success)
            d.addErrback(error)
            if results[1] is not None:
                raise results[1].value
            return results[0]

        for char in inputString:
            d = self.parser.deferFeed(char)
            realizeDeferred(d)
        d = self.parser.deferFeed(EOF)
        realizeDeferred(d)


class DefaultShiftReduceDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        self.parser = TestedDeferredParser()

    def test_shift(self):
        self.parse('2+3*4')
        self.assertEqual(self.parser.seen, [('*', 3, 4), ('+', 2, 12)])

class DefaultReduceReduceDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        class Parser(DeferredLRParser, DeferredLexer):
            def __init__(self, *args, **kwargs):
                self.seen = list()
                super().__init__(*args, **kwargs)
            @token('[a-zA-Z]+')
            def word(self, tok):
                pass
            @production('sequence -> maybeword | sequence word |')
            def seq(self):
                self.seen.append('seq')
            @production('maybeword -> word |')
            def maybe(self):
                self.seen.append('maybe')
            def deferNewSentence(self, sentence):
                return succeed(None)

        self.parser = Parser()

    def test_reduce(self):
        self.parse('')
        self.assertEqual(self.parser.seen, ['seq'])


class LeftAssociativityDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        @leftAssoc('+')
        class Parser(TestedDeferredParser):
            pass

        self.parser = Parser()

    def test_assoc(self):
        self.parse('1+2+3')
        self.assertEqual(self.parser.seen, [('+', 1, 2), ('+', 3, 3)])


class RightAssociativityDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        @rightAssoc('+')
        class Parser(TestedDeferredParser):
            pass

        self.parser = Parser()

    def test_assoc(self):
        self.parse('1+2+3')
        self.assertEqual(self.parser.seen, [('+', 2, 3), ('+', 1, 5)])


class PrecedenceDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        @leftAssoc('+')
        @leftAssoc('*')
        @nonAssoc('<')
        class Parser(TestedDeferredParser):
            @production('E -> E "<" E')
            def inf(self):
                return succeed(None)

        self.parser = Parser()

    def test_shift(self):
        self.parse('2+3*4')
        self.assertEqual(self.parser.seen, [('*', 3, 4), ('+', 2, 12)])

    def test_reduce(self):
        self.parse('2*3+4')
        self.assertEqual(self.parser.seen, [('*', 2, 3), ('+', 6, 4)])

    def test_error(self):
        try:
            self.parse('2 < 3 < 4')
        except ParseError:
            pass
        else:
            self.fail()


class OverridePrecedenceDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        @leftAssoc('+')
        @leftAssoc('mult')
        class Parser(DeferredLRParser, DeferredLexer):
            def __init__(self, *args, **kwargs):
                self.seen = list()
                super().__init__(*args, **kwargs)
            @token('[1-9][0-9]*')
            def number(self, tok):
                tok.value = int(tok.value)
            @production('E -> E<left> "+" E<right>')
            def sum(self, left, right):
                self.seen.append(('+', left, right))
                return succeed(left + right)
            @production('E -> E<left> "*" E<right>', priority='mult')
            def mult(self, left, right):
                self.seen.append(('*', left, right))
                return succeed(left * right)
            @production('E -> number<n>')
            def litteral(self, n):
                return succeed(n)
            def deferNewSentence(self, sentence):
                return succeed(None)

        self.parser = Parser()

    def test_shift(self):
        self.parse('2+3*4')
        self.assertEqual(self.parser.seen, [('*', 3, 4), ('+', 2, 12)])

    def test_reduce(self):
        self.parse('2*3+4')
        self.assertEqual(self.parser.seen, [('*', 2, 3), ('+', 6, 4)])


class ListDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        class Parser(DeferredLRParser, DeferredLexer):
            def __init__(self, testCase):
                super().__init__()
                self.testCase = testCase
            @token('[a-z]+')
            def identifier(self, tok):
                pass
            @production('L -> identifier*<tokens>')
            def idlist(self, tokens):
                return succeed(tokens)
            def deferNewSentence(self, symbol):
                self.testCase.seen = symbol
                return succeed(None)

        self.parser = Parser(self)
        self.seen = None

    def test_empty(self):
        self.parse('')
        self.assertEqual(self.seen, [])

    def test_items(self):
        self.parse('a b c')
        self.assertEqual(self.seen, ['a', 'b', 'c'])


class NonEmptyListDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        class Parser(DeferredLRParser, DeferredLexer):
            def __init__(self, testCase):
                super().__init__()
                self.testCase = testCase
            @token('[a-z]+')
            def identifier(self, tok):
                pass
            @production('L -> identifier+<tokens>')
            def idlist(self, tokens):
                return succeed(tokens)
            def deferNewSentence(self, symbol):
                self.testCase.seen = symbol
                return succeed(None)

        self.parser = Parser(self)
        self.seen = None

    def test_empty(self):
        try:
            self.parse('')
        except ParseError:
            pass
        else:
            self.fail('Got %s' % self.seen)

    def test_items(self):
        self.parse('a b c')
        self.assertEqual(self.seen, ['a', 'b', 'c'])


class SeparatorListDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        class Parser(DeferredLRParser, DeferredLexer):
            def __init__(self, testCase):
                super().__init__()
                self.testCase = testCase
            @token('[a-z]+')
            def identifier(self, tok):
                pass
            @production('L -> identifier+("|")<tokens>')
            def idlist(self, tokens):
                return succeed(tokens)
            def deferNewSentence(self, symbol):
                self.testCase.seen = symbol
                return succeed(None)

        self.parser = Parser(self)
        self.seen = None

    def test_items(self):
        self.parse('a | b | c')
        self.assertEqual(self.seen, ['a', 'b', 'c'])


class AtMostOneDeferredTestCase(DeferredParserTestCase):
    def setUp(self):
        class Parser(DeferredLRParser, DeferredLexer):
            def __init__(self, testCase):
                super().__init__()
                self.testCase = testCase
            @token('[a-z]+')
            def identifier(self, tok):
                pass
            @production('L -> identifier?<tok>')
            def idlist(self, tok):
                return succeed(tok)
            def deferNewSentence(self, symbol):
                self.testCase.seen = symbol
                return succeed(None)

        self.parser = Parser(self)
        self.seen = 1

    def test_none(self):
        self.parse('')
        self.assertEqual(self.seen, None)

    def test_value(self):
        self.parse('a')
        self.assertEqual(self.seen, 'a')

    def test_error(self):
        try:
            self.parse('a b')
        except ParseError:
            pass
        else:
            self.fail('Got %s' % self.seen)


if __name__ == '__main__':
    unittest.main()
