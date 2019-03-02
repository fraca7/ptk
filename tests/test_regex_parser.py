#!/usr/bin/env python3

import base, unittest
from ptk.regex import RegexTokenizer, RegexParser, RegularExpression, LitteralCharacterClass, \
     RegexParseError, buildRegex


class RegexParserTestCaseMixin(object):
    # It's a bit of a PITA to test for RegularExpression objects equality, so we check
    # matched strings

    def _parse(self, rx):
        return buildRegex(rx)

    def _match(self, rx, s):
        return rx.match(s)

    def test_newline(self):
        rx = self._parse(r'\n')
        self.assertTrue(self._match(rx, '\n'))

    def test_concat(self):
        rx = self._parse('ab')
        self.assertFalse(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'ab'))
        self.assertFalse(self._match(rx, 'abc'))

    def test_union(self):
        rx = self._parse('a|b')
        self.assertTrue(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'b'))
        self.assertFalse(self._match(rx, 'ab'))
        self.assertFalse(self._match(rx, 'c'))

    def test_kleene(self):
        rx = self._parse('a*')
        self.assertTrue(self._match(rx, ''))
        self.assertTrue(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'aa'))
        self.assertFalse(self._match(rx, 'b'))

    def test_closure(self):
        rx = self._parse('a+')
        self.assertFalse(self._match(rx, ''))
        self.assertTrue(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'aa'))
        self.assertFalse(self._match(rx, 'b'))

    def test_exp_single(self):
        rx = self._parse('a{2}')
        self.assertFalse(self._match(rx, ''))
        self.assertFalse(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'aa'))
        self.assertFalse(self._match(rx, 'aaa'))

    def test_exp_both(self):
        rx = self._parse('a{2-3}')
        self.assertFalse(self._match(rx, ''))
        self.assertFalse(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'aa'))
        self.assertTrue(self._match(rx, 'aaa'))
        self.assertFalse(self._match(rx, 'aaaa'))

    def test_class(self):
        rx = self._parse('[a-c]')
        self.assertTrue(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'b'))
        self.assertTrue(self._match(rx, 'c'))
        self.assertFalse(self._match(rx, 'd'))

    def test_any(self):
        rx = self._parse('.')
        self.assertTrue(self._match(rx, 'U'))
        self.assertFalse(self._match(rx, '\n'))

    def test_prio_1(self):
        rx = self._parse('a|b*')
        self.assertTrue(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'b'))
        self.assertTrue(self._match(rx, 'bb'))
        self.assertFalse(self._match(rx, 'ab'))

    def test_prio_2(self):
        rx = self._parse('ab*')
        self.assertTrue(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'ab'))
        self.assertTrue(self._match(rx, 'abb'))
        self.assertFalse(self._match(rx, 'abab'))

    def test_prio_3(self):
        rx = self._parse('a|bc')
        self.assertTrue(self._match(rx, 'a'))
        self.assertTrue(self._match(rx, 'bc'))
        self.assertFalse(self._match(rx, 'ac'))

    def test_paren(self):
        rx = self._parse('(ab)*')
        self.assertTrue(self._match(rx, 'ab'))
        self.assertTrue(self._match(rx, 'abab'))
        self.assertFalse(self._match(rx, 'abb'))

    def test_crlf(self):
        rx = self._parse(r'\r\n')
        self.assertTrue(self._match(rx, '\r\n'))

    def test_extra_tokens(self):
        try:
            rx = self._parse('ab(')
        except RegexParseError:
            pass
        else:
            self.fail()

    def test_missing_paren(self):
        try:
            rx = self._parse('(a')
        except RegexParseError:
            pass
        else:
            self.fail()


class RegexParserUnicodeTestCase(RegexParserTestCaseMixin, unittest.TestCase):
    pass


class RegexParserBytesTestCase(RegexParserTestCaseMixin, unittest.TestCase):
    def _parse(self, rx):
        if isinstance(rx, str):
            rx = rx.encode('UTF-8')
        return super()._parse(rx)

    def _match(self, rx, s):
        if isinstance(s, str):
            s = s.encode('UTF-8')
        return super()._match(rx, s)


if __name__ == '__main__':
    unittest.main()
