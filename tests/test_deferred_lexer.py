#!/usr/bin/env python3

import base, unittest

from test_lexer import EOF, LexerBasicTestCaseMixin, PositionTestCaseMixin, TokenTypeTestCaseMixin, \
     LexerByteTestCaseMixin, LexerUnicodeTestCaseMixin, LexerConsumerTestCaseMixin, \
     LexerInheritanceTestCaseMixin, LexerUnterminatedTokenTestCaseMixin, LexerLengthTestCaseMixin, \
     LexerPriorityTestCaseMixin, LexerEOFTestCaseMixin

from ptk.deferred_lexer import DeferredLexer
from twisted.internet.defer import succeed


class DeferredLexerTestCase(unittest.TestCase):
    lexerClass = DeferredLexer

    def setUp(self):
        self.tokens = list()

    def feed(self, tok):
        if tok is EOF:
            self.tokens = tuple(self.tokens)
        else:
            self.tokens.append(tok)
        return succeed(None)

    def doLex(self, inputString):
        for char in inputString:
            d = self.lexer.deferFeed(char)
            self.assertTrue(d.called)
        d = self.lexer.deferFeed(EOF)
        self.assertTrue(d.called)
        return self.tokens


class NoResultLexer(DeferredLexer):
    def deferNewToken(self, tok):
        return succeed(None)


class DeferredLexerBasicTestCase(LexerBasicTestCaseMixin, DeferredLexerTestCase):
    pass


class DeferredLexerPositionTestCase(PositionTestCaseMixin, DeferredLexerTestCase):
    lexerClass = NoResultLexer


class DeferredLexerTokenTypeTestCase(TokenTypeTestCaseMixin, DeferredLexerTestCase):
    lexerClass = NoResultLexer


class DeferredLexerByteTestCase(LexerByteTestCaseMixin, DeferredLexerTestCase):
    pass


class DeferredLexerUnicodeTestCase(LexerUnicodeTestCaseMixin, DeferredLexerTestCase):
    pass


class DeferredLexerConsumerTestCase(LexerConsumerTestCaseMixin, DeferredLexerTestCase):
    pass


class DeferredLexerInheritanceTestCase(LexerInheritanceTestCaseMixin, DeferredLexerTestCase):
    pass


class DeferredLexerUnterminatedTokenTestCase(LexerUnterminatedTokenTestCaseMixin, DeferredLexerTestCase):
    pass


class DeferredLexerLengthTestCase(LexerLengthTestCaseMixin, DeferredLexerTestCase):
    pass


class DeferredLexerPriorityTestCase(LexerPriorityTestCaseMixin, DeferredLexerTestCase):
    pass


class DeferredLexerEOFTestCase(LexerEOFTestCaseMixin, DeferredLexerTestCase):
    pass


if __name__ == '__main__':
    unittest.main()
