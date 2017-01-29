#!/usr/bin/env python

import six
import base, unittest

from ptk.lexer import LexerError, token, EOF
from ptk.lexer import ProgressiveLexer, ReLexer


class LexerUnderTestMixin(object):
    def __init__(self, testCase):
        self.testCase = testCase
        super(LexerUnderTestMixin, self).__init__()

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
        super(LexerBasicTestCaseMixin, self).setUp()
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
        self.assertEqual(self.doLex('abc'), (('ID', 'abc'),))

    def test_ignore_leading(self):
        self.assertEqual(self.doLex('  abc'), (('ID', 'abc'),))

    def test_ignore_middle(self):
        self.assertEqual(self.doLex('a bc'), (('ID', 'a'), ('ID', 'bc')))

    def test_ignore_trailing(self):
        self.assertEqual(self.doLex('abc  '), (('ID', 'abc'),))

    def test_value(self):
        self.assertEqual(self.doLex('42'), (('NUMBER', 42),))

    def test_forced_value_eof(self):
        self.assertEqual(self.doLex('abc\n'), (('ID', 'abc'),))

    def test_forced_value(self):
        self.assertEqual(self.doLex('0xf'), (('NUMBER', 15),))

    def test_ignore(self):
        self.assertEqual(self.doLex('a++b'), (('ID', 'a'), ('ID', 'b')))

    def test_tokenvalues(self):
        self.assertEqual(self.lexer.tokenTypes(), set(['ID', 'NUMBER', 'INC']))


class ProgressiveLexerBasicTestCase(LexerBasicTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerBasicTestCase(LexerBasicTestCaseMixin, ReLexerTestCase):
    pass


class PositionTestCaseMixin(object):
    def setUp(self):
        super(PositionTestCaseMixin, self).setUp()
        class TestedLexer(self.lexerClass):
            @staticmethod
            def ignore(char):
                return char in [' ', '\n']
            @token('[a-z]')
            def letter(self, tok):
                pass
            def newToken(self, tok):
                pass

        self.lexer = TestedLexer()

    def test_position(self):
        try:
            self.doLex('ab\ncd0aa')
        except LexerError as exc:
            self.assertEqual(exc.lineno, 2)
            self.assertEqual(exc.colno, 3)
        else:
            self.fail()


class ProgressiveLexerPositionTestCase(PositionTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerPositionTestCase(PositionTestCaseMixin, ReLexerTestCase):
    pass


class TokenTypeTestCaseMixin(object):
    def setUp(self):
        super(TokenTypeTestCaseMixin, self).setUp()
        class TestedLexer(self.lexerClass):
            def __init__(self, testCase):
                self.testCase = testCase
                super(TestedLexer, self).__init__()
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
        super(LexerByteTestCaseMixin, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token(six.b('[a-zA-Z]+'))
            def ID(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_byte_regex_gives_byte_token_value(self):
        tok, = self.doLex(six.b('foo'))
        self.assertTrue(isinstance(tok.value, six.binary_type))


class ProgressiveLexerByteTestCase(LexerByteTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerByteTestCase(LexerByteTestCaseMixin, ReLexerTestCase):
    pass


class LexerUnicodeTestCaseMixin(object):
    def setUp(self):
        super(LexerUnicodeTestCaseMixin, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token(six.u('[a-zA-Z]+'))
            def ID(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_unicode_regex_gives_unicode_token_value(self):
        tok, = self.doLex(six.u('foo'))
        if six.PY2:
            self.assertTrue(isinstance(tok.value, unicode))
        else:
            self.assertTrue(isinstance(tok.value, str))


class ProgressiveLexerUnicodeTestCase(LexerUnicodeTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerUnicodeTestCase(LexerUnicodeTestCaseMixin, ReLexerTestCase):
    pass


class LexerUnambiguousTestCase(ProgressiveLexerTestCase):
    def setUp(self):
        super(LexerUnambiguousTestCase, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('a')
            def ID(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_unambiguous(self):
        # If we arrive in a final state without any outgoing transition, it should be an instant match.
        self.lexer.feed('a')
        self.assertEqual(self.tokens, [('ID', 'a')]) # Still a list because no EOF



class LexerConsumerTestCaseMixin(object):
    def setUp(self):
        super(LexerConsumerTestCaseMixin, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('[a-zA-Z0-9]+')
            def ID(self, tok):
                pass
            @token('"')
            def STR(self, tok):
                class StringBuilder(object):
                    def __init__(self):
                        self.value = six.StringIO()
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
        self.assertEqual(self.doLex(r'ab"foo\"spam"eggs'), (('ID', 'ab'), ('STR', 'foo"spam'), ('ID', 'eggs')))


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
        super(LexerInheritanceTestCaseMixin, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('[0-9]')
            def digit(self, tok):
                pass

        class ChildLexer(TestedLexer):
            def digit(self, tok):
                tok.value = int(tok.value)

        self.lexer = ChildLexer(self)

    def test_inherit(self):
        self.assertEqual(self.doLex('4'), (('digit', 4),))


class ProgressiveLexerInheritanceTestCase(LexerInheritanceTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerInheritanceTestCase(LexerInheritanceTestCaseMixin, ReLexerTestCase):
    pass


class LexerUnterminatedTokenTestCaseMixin(object):
    def setUp(self):
        super(LexerUnterminatedTokenTestCaseMixin, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('abc')
            def ID(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_simple(self):
        self.assertEqual(self.doLex('abc'), (('ID', 'abc'),))

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
        super(LexerLengthTestCaseMixin, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('<|=')
            def LT(self, tok):
                pass
            @token('<=')
            def LTE(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_longest(self):
        self.assertEqual(self.doLex('<='), (('LTE', '<='),))


class ProgressiveLexerLengthTestCase(LexerLengthTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerLengthTestCase(LexerLengthTestCaseMixin, ReLexerTestCase):
    pass


class LexerPriorityTestCaseMixin(object):
    def setUp(self):
        super(LexerPriorityTestCaseMixin, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('a|b')
            def A(self, tok):
                pass
            @token('b|c')
            def B(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_priority(self):
        self.assertEqual(self.doLex('b'), (('A', 'b'),))


class ProgressiveLexerPriorityTestCase(LexerPriorityTestCaseMixin, ProgressiveLexerTestCase):
    pass


class ReLexerPriorityTestCase(LexerPriorityTestCaseMixin, ReLexerTestCase):
    pass


class LexerRemainingCharactersTestCase(ProgressiveLexerTestCase):
    def setUp(self):
        super(LexerRemainingCharactersTestCase, self).setUp()
        class TestedLexer(LexerUnderTestMixin, self.lexerClass):
            @token('abc')
            def ID1(self, tok):
                pass
            @token('aba')
            def ID2(self, tok):
                pass
        self.lexer = TestedLexer(self)

    def test_remain(self):
        self.assertEqual(self.doLex('abaaba'), (('ID2', 'aba'), ('ID2', 'aba')))


class LexerEOFTestCaseMixin(object):
    def setUp(self):
        super(LexerEOFTestCaseMixin, self).setUp()
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
