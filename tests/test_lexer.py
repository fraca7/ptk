#!/usr/bin/env python3

import io
import base, unittest

from ptk.lexer import LexerError, token, EOF, LexerPosition
from ptk.lexer import ProgressiveLexer, ReLexer


class LexerUnderTestMixin(object):
    def __init__(self, testCase):
        self.testCase = testCase
        super().__init__()

    def newToken(self, tok):
        self.testCase.feed(tok)

    def deferNewToken(self, tok):
        self.testCase.feed(tok)
        from twisted.internet.defer import succeed
        return succeed(None)


class LexerTestCase(unittest.TestCase):
    def setUp(self):
        self.tokens = list()

    def feed(self, tok):
        if tok is EOF:
            self.tokens = tuple(self.tokens) # So that any more tokens will raise an exception
        else:
            self.tokens.append(tok)

    def doLex(self, inputString):
        self.lexer.parse(inputString)
        return self.tokens


class ProgressiveLexerTestCase(LexerTestCase):
    lexerClass = ProgressiveLexer


class ReLexerTestCase(LexerTestCase):
    lexerClass = ReLexer


class LexerBasicTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('[a-zA-Z]+')
            def ID(self, tok):
                pass
            @token('[0-9]+')
            def NUMBER(self, tok):
                tok.value = int(tok.value)
            @token('\n', types=[EOF])
            def EOL(self, tok):
                tok.type = EOF
            @token('0x[a-fA-F0-9]+', types=['NUMBER'])
            def HEX(self, tok):
                tok.type = 'NUMBER'
                tok.value = int(tok.value, 16)
            @token(r'\+\+')
            def INC(self, tok):
                tok.type = None
        self.lexer = TestedLexer(self)

    def test_single(self):
        token, = self.doLex('abc')
        self.assertEqual((token.type, token.value), ('ID', 'abc'))

    def test_ignore_leading(self):
        token, = self.doLex('  abc')
        self.assertEqual((token.type, token.value), ('ID', 'abc'))

    def test_ignore_middle(self):
        tok1, tok2 = self.doLex('a bc')
        self.assertEqual((tok1.type, tok1.value), ('ID', 'a'))
        self.assertEqual((tok2.type, tok2.value), ('ID', 'bc'))

    def test_ignore_trailing(self):
        token, = self.doLex('abc  ')
        self.assertEqual((token.type, token.value), ('ID', 'abc'))

    def test_value(self):
        token, = self.doLex('42')
        self.assertEqual((token.type, token.value), ('NUMBER', 42))

    def test_forced_value_eof(self):
        token, = self.doLex('abc\n')
        self.assertEqual((token.type, token.value), ('ID', 'abc'))

    def test_forced_value(self):
        token, = self.doLex('0xf')
        self.assertEqual((token.type, token.value), ('NUMBER', 15))

    def test_ignore(self):
        tok1, tok2 = self.doLex('a++b')
        self.assertEqual((tok1.type, tok1.value), ('ID', 'a'))
        self.assertEqual((tok2.type, tok2.value), ('ID', 'b'))

    def test_tokenvalues(self):
        self.assertEqual(self.lexer.tokenTypes(), set(['ID', 'NUMBER', 'INC']))


class ProgressiveLexerBasicTestCase(LexerBasicTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerBasicTestCase(LexerBasicTestCaseMixin, ReLexerTestCase):
    pass


class PositionTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @staticmethod
            def ignore(char):
                return char in [' ', '\n']
            @token('[a-z]+')
            def identifier(self, tok):
                pass

        self.lexer = TestedLexer(testCase=self)

    def test_error_position(self):
        try:
            self.doLex('ab\ncd0aa')
        except LexerError as exc:
            self.assertEqual(exc.lineno, 2)
            self.assertEqual(exc.colno, 3)
        else:
            self.fail()

    def test_token_positions(self):
        tok1, tok2 = self.doLex('ab\n  int')
        self.assertEqual(tok1.position, LexerPosition(column=1, line=1))
        self.assertEqual(tok2.position, LexerPosition(column=3, line=2))


class ProgressiveLexerPositionTestCase(PositionTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerPositionTestCase(PositionTestCaseMixin, ReLexerTestCase):
    pass


class TokenTypeTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(self.lexerClass):
            def __init__(self, testCase):
                self.testCase = testCase
                super().__init__()
            @token('[a-z]', types=['LETTER'])
            def letter(self, tok):
                self.testCase.assertTrue(tok.type is None)
            def newToken(self, tok):
                pass
          
        self.lexer = TestedLexer(self)

    def test_none(self):
        self.doLex('a')

    def test_funcname(self):
        self.assertFalse('letter' in self.lexer.tokenTypes())

    def test_types(self):
        self.assertTrue('LETTER' in self.lexer.tokenTypes())


class ProgressiveLexerTokenTypeTestCase(TokenTypeTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerTokenTypeTestCase(TokenTypeTestCaseMixin, ReLexerTestCase):
    pass


class LexerByteTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token(b'[a-zA-Z]+')
            def ID(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_byte_regex_gives_byte_token_value(self):
        tok, = self.doLex(b'foo')
        self.assertTrue(isinstance(tok.value, bytes))


class ProgressiveLexerByteTestCase(LexerByteTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerByteTestCase(LexerByteTestCaseMixin, ReLexerTestCase):
    pass


class LexerUnicodeTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('[a-zA-Z]+')
            def ID(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_unicode_regex_gives_unicode_token_value(self):
        tok, = self.doLex('foo')
        self.assertTrue(isinstance(tok.value, str))


class ProgressiveLexerUnicodeTestCase(LexerUnicodeTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerUnicodeTestCase(LexerUnicodeTestCaseMixin, ReLexerTestCase):
    pass


class LexerUnambiguousTestCase(ProgressiveLexerTestCase):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('a')
            def ID(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_unambiguous(self):
        # If we arrive in a final state without any outgoing transition, it should be an instant match.
        self.lexer.feed('a')
        token, = self.tokens
        self.assertEqual((token.type, token.value), ('ID', 'a'))



class LexerConsumerTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('[a-zA-Z0-9]+')
            def ID(self, tok):
                pass
            @token('"')
            def STR(self, tok):
                class StringBuilder(object):
                    def __init__(self):
                        self.value = io.StringIO()
                        self.state = 0
                    def feed(self, char):
                        if self.state == 0:
                            if char == '\\':
                                self.state = 1
                            elif char == '"':
                                return 'STR', self.value.getvalue()
                            else:
                                self.value.write(char)
                        elif self.state == 1:
                            self.value.write(char)
                            self.state = 0
                self.setConsumer(StringBuilder())
        self.lexer = TestedLexer(self)

    def test_string(self):
        tok1, tok2, tok3 = self.doLex(r'ab"foo\"spam"eggs')
        self.assertEqual((tok1.type, tok1.value), ('ID', 'ab'))
        self.assertEqual((tok2.type, tok2.value), ('STR', 'foo"spam'))
        self.assertEqual((tok3.type, tok3.value), ('ID', 'eggs'))


class ProgressiveLexerConsumerTestCase(LexerConsumerTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerConsumerTestCase(LexerConsumerTestCaseMixin, ReLexerTestCase):
    pass


class LexerDuplicateTokenNameTestCaseMixin(object):
    def test_dup(self):
        try:
            class TestedLexer(LexerUnderTestMixin, self.lexerClass):
                @token('a')
                def ID(self, tok):
                    pass
                @token('b')
                def ID(self, tok):
                    pass
        except TypeError:
            pass
        else:
            self.fail()

class ProgressiveLexerDuplicateTokenNameTestCase(LexerDuplicateTokenNameTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerDuplicateTokenNameTestCase(LexerDuplicateTokenNameTestCaseMixin, ReLexerTestCase):
    pass


class LexerInheritanceTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('[0-9]')
            def digit(self, tok):
                pass

        class ChildLexer(TestedLexer):
            def digit(self, tok):
                tok.value = int(tok.value)

        self.lexer = ChildLexer(self)

    def test_inherit(self):
        token, = self.doLex('4')
        self.assertEqual((token.type, token.value), ('digit', 4))


class ProgressiveLexerInheritanceTestCase(LexerInheritanceTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerInheritanceTestCase(LexerInheritanceTestCaseMixin, ReLexerTestCase):
    pass


class LexerUnterminatedTokenTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('abc')
            def ID(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_simple(self):
        token, = self.doLex('abc')
        self.assertEqual((token.type, token.value), ('ID', 'abc'))

    def test_unterminated(self):
        try:
            self.doLex('ab')
        except LexerError:
            pass
        else:
            self.fail()


class ProgressiveLexerUnterminatedTokenTestCase(LexerUnterminatedTokenTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerUnterminatedTokenTestCase(LexerUnterminatedTokenTestCaseMixin, ReLexerTestCase):
    pass


class LexerLengthTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('<|=')
            def LT(self, tok):
                pass
            @token('<=')
            def LTE(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_longest(self):
        token, = self.doLex('<=')
        self.assertEqual((token.type, token.value), ('LTE', '<='))


class ProgressiveLexerLengthTestCase(LexerLengthTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerLengthTestCase(LexerLengthTestCaseMixin, ReLexerTestCase):
    pass


class LexerPriorityTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('a|b')
            def A(self, tok):
                pass
            @token('b|c')
            def B(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_priority(self):
        token, = self.doLex('b')
        self.assertEqual((token.type, token.value), ('A', 'b'))


class ProgressiveLexerPriorityTestCase(LexerPriorityTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerPriorityTestCase(LexerPriorityTestCaseMixin, ReLexerTestCase):
    pass


class LexerRemainingCharactersTestCase(ProgressiveLexerTestCase):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('abc')
            def ID1(self, tok):
                pass
            @token('aba')
            def ID2(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_remain(self):
        t1, t2 = self.doLex('abaaba')
        self.assertEqual((t1.type, t1.value), ('ID2', 'aba'))
        self.assertEqual((t2.type, t2.value), ('ID2', 'aba'))


class LexerEOFTestCaseMixin(object):
    def setUp(self):
        super().setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token(r'[0-9]+')
            def NUMBER(self, tok):
                tok.value = int(tok.value)
            @token(r'\n')
            def EOL(self, tok):
                tok.type = EOF
        self.lexer = TestedLexer(self)

    def test_eol_is_eof(self):
        self.lexer.parse('42\n')
        self.assertTrue(isinstance(self.tokens, tuple))


class ProgressiveLexerEOFTestCase(LexerEOFTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerEOFTestCase(LexerEOFTestCaseMixin, ReLexerTestCase):
    pass


if __name__ == '__main__':
    unittest.main()
