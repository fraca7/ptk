#!/usr/bin/env python3

import base, unittest

from ptk.regex import RegularExpression, LitteralCharacterClass


class RegexTestMixin(object):
    def test_deadend(self):
        rx = RegularExpression.concat(
            RegularExpression.fromClass(LitteralCharacterClass(self.t('<')[0])),
            RegularExpression.fromClass(LitteralCharacterClass(self.t('=')[0]))
            )
        rx.start()
        rx.feed(self.t('<')[0]) # byte/char
        self.assertFalse(rx.isDeadEnd())

    def test_newline(self):
        rx = RegularExpression.fromClass(LitteralCharacterClass(self.t('\n')[0]))
        self.assertTrue(rx.match(self.t('\n')))

    def test_class(self):
        rx = RegularExpression.fromClass(LitteralCharacterClass(self.t('a')[0]))
        self.assertTrue(rx.match(self.t('a')))
        self.assertFalse(rx.match(self.t('b')))

    def test_concat(self):
        rx = RegularExpression.concat(
            RegularExpression.fromClass(LitteralCharacterClass(self.t('a')[0])),
            RegularExpression.fromClass(LitteralCharacterClass(self.t('b')[0])),
            RegularExpression.fromClass(LitteralCharacterClass(self.t('c')[0]))
            )
        self.assertTrue(rx.match(self.t('abc')))
        self.assertFalse(rx.match(self.t('ab')))

    def test_union(self):
        rx = RegularExpression.union(
            RegularExpression.fromClass(LitteralCharacterClass(self.t('a')[0])),
            RegularExpression.fromClass(LitteralCharacterClass(self.t('b')[0])),
            RegularExpression.fromClass(LitteralCharacterClass(self.t('c')[0]))
            )
        self.assertTrue(rx.match(self.t('a')))
        self.assertTrue(rx.match(self.t('b')))
        self.assertTrue(rx.match(self.t('c')))
        self.assertFalse(rx.match(self.t('d')))

    def test_kleene(self):
        rx = RegularExpression.kleene(RegularExpression.fromClass(LitteralCharacterClass(self.t('a')[0])))
        self.assertTrue(rx.match(self.t('')))
        self.assertTrue(rx.match(self.t('a')))
        self.assertTrue(rx.match(self.t('aa')))
        self.assertFalse(rx.match(self.t('ab')))

    def test_exponent(self):
        rx = RegularExpression.exponent(RegularExpression.fromClass(LitteralCharacterClass(self.t('a')[0])), 2, 3)
        self.assertFalse(rx.match(self.t('a')))
        self.assertTrue(rx.match(self.t('aa')))
        self.assertTrue(rx.match(self.t('aaa')))
        self.assertFalse(rx.match(self.t('aaaa')))

    def test_exponent_min(self):
        rx = RegularExpression.exponent(RegularExpression.fromClass(LitteralCharacterClass(self.t('a')[0])), 2)
        self.assertFalse(rx.match(self.t('a')))
        self.assertTrue(rx.match(self.t('aa')))
        self.assertTrue(rx.match(self.t('aaa')))

    def test_exponent_null(self):
        rx = RegularExpression.exponent(RegularExpression.fromClass(LitteralCharacterClass(self.t('a')[0])), 0, 1)
        self.assertTrue(rx.match(self.t('')))
        self.assertTrue(rx.match(self.t('a')))
        self.assertFalse(rx.match(self.t('aa')))


class UnicodeRegexTest(RegexTestMixin, unittest.TestCase):
    def t(self, s):
        return s


class BytesRegexTest(RegexTestMixin, unittest.TestCase):
    def t(self, s):
        return s.encode('ascii')


if __name__ == '__main__':
    unittest.main()
