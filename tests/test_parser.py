#!/usr/bin/env python3

import base, unittest

from ptk.parser import LRParser, ParseError, leftAssoc, rightAssoc, nonAssoc
from ptk.lexer import ProgressiveLexer, token, EOF
from ptk.grammar import production


class TestedParser(LRParser, ProgressiveLexer):
    def __init__(self, *args, **kwargs):
        self.seen = list()
        super().__init__(*args, **kwargs)

    @token('[1-9][0-9]*')
    def number(self, tok):
        tok.value = int(tok.value)

    @production('E -> E<left> "+" E<right>')
    def sum(self, left, right):
        self.seen.append(('+', left, right))
        return left + right

    @production('E -> E<left> "*" E<right>')
    def mult(self, left, right):
        self.seen.append(('*', left, right))
        return left * right

    @production('E -> number<n>')
    def litteral(self, n):
        return n

    def newSentence(self, sentence):
        pass


class DefaultShiftReduceTestCase(unittest.TestCase):
    def setUp(self):
        self.parser = TestedParser()

    def test_shift(self):
        self.parser.parse('2+3*4')
        self.assertEqual(self.parser.seen, [('*', 3, 4), ('+', 2, 12)])


class DefaultReduceReduceTestCase(unittest.TestCase):
    def setUp(self):
        class Parser(LRParser, ProgressiveLexer):
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
            def newSentence(self, sentence):
                pass

        self.parser = Parser()

    def test_reduce(self):
        self.parser.parse('')
        self.assertEqual(self.parser.seen, ['seq'])


class LeftAssociativityTestCase(unittest.TestCase):
    def setUp(self):
        @leftAssoc('+')
        class Parser(TestedParser):
            pass

        self.parser = Parser()

    def test_assoc(self):
        self.parser.parse('1+2+3')
        self.assertEqual(self.parser.seen, [('+', 1, 2), ('+', 3, 3)])


class RightAssociativityTestCase(unittest.TestCase):
    def setUp(self):
        @rightAssoc('+')
        class Parser(TestedParser):
            pass

        self.parser = Parser()

    def test_assoc(self):
        self.parser.parse('1+2+3')
        self.assertEqual(self.parser.seen, [('+', 2, 3), ('+', 1, 5)])


class PrecedenceTestCase(unittest.TestCase):
    def setUp(self):
        @leftAssoc('+')
        @leftAssoc('*')
        @nonAssoc('<')
        class Parser(TestedParser):
            @production('E -> E "<" E')
            def inf(self):
                pass

        self.parser = Parser()

    def test_shift(self):
        self.parser.parse('2+3*4')
        self.assertEqual(self.parser.seen, [('*', 3, 4), ('+', 2, 12)])

    def test_reduce(self):
        self.parser.parse('2*3+4')
        self.assertEqual(self.parser.seen, [('*', 2, 3), ('+', 6, 4)])

    def test_error(self):
        try:
            self.parser.parse('2 < 3 < 4')
        except ParseError:
            pass
        else:
            self.fail()


class OverridePrecedenceTestCase(unittest.TestCase):
    def setUp(self):
        @leftAssoc('+')
        @leftAssoc('mult')
        class Parser(LRParser, ProgressiveLexer):
            def __init__(self, *args, **kwargs):
                self.seen = list()
                super().__init__(*args, **kwargs)
            @token('[1-9][0-9]*')
            def number(self, tok):
                tok.value = int(tok.value)
            @production('E -> E<left> "+" E<right>')
            def sum(self, left, right):
                self.seen.append(('+', left, right))
                return left + right
            @production('E -> E<left> "*" E<right>', priority='mult')
            def mult(self, left, right):
                self.seen.append(('*', left, right))
                return left * right
            @production('E -> number<n>')
            def litteral(self, n):
                return n
            def newSentence(self, sentence):
                pass

        self.parser = Parser()

    def test_shift(self):
        self.parser.parse('2+3*4')
        self.assertEqual(self.parser.seen, [('*', 3, 4), ('+', 2, 12)])

    def test_reduce(self):
        self.parser.parse('2*3+4')
        self.assertEqual(self.parser.seen, [('*', 2, 3), ('+', 6, 4)])


class LRTestCase(unittest.TestCase):
    def setUp(self):
        class Parser(LRParser, ProgressiveLexer):
            @token('a')
            def identifier(self, tok):
                pass
            @production('S -> G "=" D | D')
            def s(self):
                pass
            @production('G -> "*" D | identifier')
            def g(self):
                pass
            @production('D -> G')
            def d(self):
                pass

        self.parser = Parser()

    def test_no_conflicts(self):
        self.assertEqual(self.parser.nSR, 0)


class ListTestCase(unittest.TestCase):
    def setUp(self):
        class Parser(LRParser, ProgressiveLexer):
            def __init__(self, testCase):
                super().__init__()
                self.testCase = testCase
            @token('[a-z]+')
            def identifier(self, tok):
                pass
            @production('L -> identifier*<tokens>')
            def idlist(self, tokens):
                return tokens
            def newSentence(self, symbol):
                self.testCase.seen = symbol

        self.parser = Parser(self)
        self.seen = None

    def test_empty(self):
        self.parser.parse('')
        self.assertEqual(self.seen, [])

    def test_items(self):
        self.parser.parse('a b c')
        self.assertEqual(self.seen, ['a', 'b', 'c'])


class NonEmptyListTestCase(unittest.TestCase):
    def setUp(self):
        class Parser(LRParser, ProgressiveLexer):
            def __init__(self, testCase):
                super().__init__()
                self.testCase = testCase
            @token('[a-z]+')
            def identifier(self, tok):
                pass
            @production('L -> identifier+<tokens>')
            def idlist(self, tokens):
                return tokens
            def newSentence(self, symbol):
                self.testCase.seen = symbol

        self.parser = Parser(self)
        self.seen = None

    def test_empty(self):
        try:
            self.parser.parse('')
        except ParseError:
            pass
        else:
            self.fail('Got %s' % self.seen)

    def test_items(self):
        self.parser.parse('a b c')
        self.assertEqual(self.seen, ['a', 'b', 'c'])


class SeparatorListTestCase(unittest.TestCase):
    def setUp(self):
        class Parser(LRParser, ProgressiveLexer):
            def __init__(self, testCase):
                super().__init__()
                self.testCase = testCase
            @token('[a-z]+')
            def identifier(self, tok):
                pass
            @production('L -> identifier+("|")<tokens>')
            def idlist(self, tokens):
                return tokens
            def newSentence(self, symbol):
                self.testCase.seen = symbol

        self.parser = Parser(self)
        self.seen = None

    def test_items(self):
        self.parser.parse('a | b | c')
        self.assertEqual(self.seen, ['a', 'b', 'c'])


class AtMostOneTestCase(unittest.TestCase):
    def setUp(self):
        class Parser(LRParser, ProgressiveLexer):
            def __init__(self, testCase):
                super().__init__()
                self.testCase = testCase
            @token('[a-z]+')
            def identifier(self, tok):
                pass
            @production('L -> identifier?<tok>')
            def idlist(self, tok):
                return tok
            def newSentence(self, symbol):
                self.testCase.seen = symbol

        self.parser = Parser(self)
        self.seen = 1

    def test_none(self):
        self.parser.parse('')
        self.assertEqual(self.seen, None)

    def test_value(self):
        self.parser.parse('a')
        self.assertEqual(self.seen, 'a')

    def test_error(self):
        try:
            self.parser.parse('a b')
        except ParseError:
            pass
        else:
            self.fail('Got %s' % self.seen)


class InheritanceTestCase(unittest.TestCase):
    def setUp(self):
        class Parser(LRParser, ProgressiveLexer):
            def __init__(self):
                self.seen = None
                super().__init__()
            @token('[0-9]')
            def digit(self, tok):
                tok.value = int(tok.value)
            @production('E -> digit<d>')
            def start(self, d):
                pass
            def newSentence(self, symbol):
                self.seen = symbol

        class Child(Parser):
            def start(self, d):
                return d

        self.parser = Child()

    def test_override(self):
        self.parser.parse('4')
        self.assertEqual(self.parser.seen, 4)


if __name__ == '__main__':
    unittest.main()
