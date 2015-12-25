#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import six
import base, unittest

from ptk.regex import TokenizeError, RegexTokenizer, \
     BackslashAtEndOfInputError, UnterminatedClassError, \
     InvalidClassError, InvalidExponentError, \
     CharacterClass, RegexCharacterClass, LitteralCharacterClass, \
     AnyCharacterClass, ExponentToken, TokenizeError


class TokenizerTestCase(unittest.TestCase):
    def _tokenize(self, regex):
        if six.PY2 and isinstance(regex, str):
            regex = regex.decode('UTF-8')

        tokenizer = RegexTokenizer(regex)
        return list(tokenizer.tokens())


class BasicTestCase(TokenizerTestCase):
    def test_close_bracket(self):
        try:
            self._tokenize('foo]')
        except TokenizeError:
            pass
        else:
            self.fail('Did not raise TokenizeError')

    def test_close_brace(self):
        try:
            self._tokenize('foo}')
        except TokenizeError:
            pass
        else:
            self.fail('Did not raise TokenizeError')


class ConcatTestCase(TokenizerTestCase):
    def test_concat(self):
        self.assertEqual(self._tokenize('abc'), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('a'))),
                                                 (RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('b'))),
                                                 (RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('c')))])

    def test_escape(self):
        self.assertEqual(self._tokenize(r'\[\n'), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('['))),
                                                   (RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('\n')))])

    def test_error(self):
        try:
            self._tokenize('spam\\')
        except BackslashAtEndOfInputError:
            pass
        else:
            self.fail('Did not raise BackslashAtEndOfInputError')


class RangeTestCase(TokenizerTestCase):
    def test_cache(self):
        rx1 = RegexCharacterClass(six.u('[a-z]'))
        rx2 = RegexCharacterClass(six.u('[a-z]'))
        self.assertTrue(rx1._rx is rx2._rx)

    def test_unterminated(self):
        try:
            self._tokenize('[acb')
        except UnterminatedClassError:
            pass
        else:
            self.fail('Did not raise UnterminatedClassError')

    def test_invalid(self):
        try:
            self._tokenize('[b-a]')
        except InvalidClassError:
            pass
        else:
            self.fail('Did not raise InvalidClassError')

    def _test_range(self, rx, testin, testout):
        tokens = self._tokenize(rx)
        self.assertEqual(len(tokens), 1)
        type_, value = tokens[0]
        self.assertEqual(type_, RegexTokenizer.TOK_CLASS)
        self.assertTrue(isinstance(value, CharacterClass))
        for item in testin:
            item = item.decode('UTF-8') if six.PY2 and isinstance(item, str) else item
            self.assertTrue(item in value, '"%s" should match "%s"' % (item, rx))
        for item in testout:
            item = item.decode('UTF-8') if six.PY2 and isinstance(item, str) else item
            self.assertFalse(item in value, '"%s" should not match "%s"' % (item, rx))

    def test_simple(self):
        self._test_range('[acb]', ['a', 'b', 'c'], [' ', 'd'])

    def test_range(self):
        self._test_range('[a-d]', ['a', 'b', 'c', 'd'], [' ', 'e'])

    def test_ranges(self):
        self._test_range('[a-cf-h]', ['a', 'b', 'c', 'f', 'g', 'h'], [' ', 'd', 'e', 'i'])

    def test_minus(self):
        self._test_range('[-a-c]', ['-', 'a', 'b', 'c'], [' ', 'd'])

    def test_special(self):
        self._test_range('[a|]', ['a', '|'], [' ', 'b'])

    def test_escape(self):
        self._test_range(r'[a\]]', ['a', ']'], [' ', 'b'])

    def test_escape_start(self):
        self._test_range(r'[\]-^]', [']', '^'], ['a'])

    def test_escape_end(self):
        self._test_range(r'[\\-\]]', ['\\', ']'], ['a'])

    def test_class_w(self):
        self._test_range(r'\w', [six.u('\u00E9')], ['~'])

    def test_class_d_class(self):
        self._test_range(r'[\wa]', [six.u('\u00E9'), 'a'], ['~'])

    def test_class_d(self):
        self._test_range(r'\d', ['0'], ['a'])

    def test_any(self):
        self.assertEqual(self._tokenize('a.'), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('a'))),
                                                (RegexTokenizer.TOK_CLASS, AnyCharacterClass())])


class ExponentTestCase(TokenizerTestCase):
    def test_invalid(self):
        try:
            self._tokenize('a{b}')
        except InvalidExponentError:
            pass
        else:
            self.fail('Did not raise InvalidExponentError')

    def test_invalid_2(self):
        try:
            self._tokenize('a{1b}')
        except InvalidExponentError:
            pass
        else:
            self.fail('Did not raise InvalidExponentError')

    def test_invalid_3(self):
        try:
            self._tokenize('a{1-2b}')
        except InvalidExponentError:
            pass
        else:
            self.fail('Did not raise InvalidExponentError')

    def test_invalid_end(self):
        try:
            self._tokenize('a{1-a}')
        except InvalidExponentError:
            pass
        else:
            self.fail('Did not raise InvalidExponentError')

    def test_unterminated(self):
        try:
            self._tokenize('a{1')
        except InvalidExponentError:
            pass
        else:
            self.fail('Did not raise InvalidExponentError')

    def test_unterminated_value(self):
        try:
            self._tokenize('a{1-}')
        except InvalidExponentError:
            pass
        else:
            self.fail('Did not raise InvalidExponentError')

    def test_start(self):
        try:
            self._tokenize('a{-2}')
        except InvalidExponentError:
            pass
        else:
            self.fail('Did not raise InvalidExponentError')

    def test_invert(self):
        try:
            self._tokenize('a{2-1}')
        except InvalidExponentError:
            pass
        else:
            self.fail('Did not raise InvalidExponentError')

    def test_single_value(self):
        self.assertEqual(self._tokenize('a{42}'), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('a'))),
                                                   (RegexTokenizer.TOK_EXPONENT, ExponentToken(42, 42))])

    def test_interval(self):
        self.assertEqual(self._tokenize('a{13-15}'), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('a'))),
                                                      (RegexTokenizer.TOK_EXPONENT, ExponentToken(13, 15))])

    def test_kleene(self):
        self.assertEqual(self._tokenize('a*'), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('a'))),
                                                (RegexTokenizer.TOK_EXPONENT, ExponentToken(0, None))])

    def test_closure(self):
        self.assertEqual(self._tokenize('a+'), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('a'))),
                                                (RegexTokenizer.TOK_EXPONENT, ExponentToken(1, None))])


class SymbolTestMixin(object):
    token = None # Subclass responsibility

    def test_start(self):
        self.assertEqual(self._tokenize(r'{symbol}s'.format(symbol=self.symbol[1])), [self.symbol,
                                                                                      (RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('s')))])

    def test_middle(self):
        self.assertEqual(self._tokenize(r's{symbol}e'.format(symbol=self.symbol[1])), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('s'))),
                                                                                       self.symbol,
                                                                                       (RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('e')))])

    def test_end(self):
        self.assertEqual(self._tokenize(r's{symbol}'.format(symbol=self.symbol[1])), [(RegexTokenizer.TOK_CLASS, LitteralCharacterClass(six.u('s'))),
                                                                                      self.symbol])


class LParenTestCase(SymbolTestMixin, TokenizerTestCase):
    symbol = (RegexTokenizer.TOK_LPAREN, six.u('('))


class RParenTestCase(SymbolTestMixin, TokenizerTestCase):
    symbol = (RegexTokenizer.TOK_RPAREN, six.u(')'))


class UnionTestCase(SymbolTestMixin, TokenizerTestCase):
    symbol = (RegexTokenizer.TOK_UNION, six.u('|'))


if __name__ == '__main__':
    unittest.main()
