#!/usr/bin/env python

import six
import base, unittest

from ptk.regex import RegularExpression, LitteralCharacterClass


class RegexTest(unittest.TestCase):
    def test_deadend(self):
        rx = RegularExpression.concat(
            RegularExpression.fromClass(LitteralCharacterClass('<')),
            RegularExpression.fromClass(LitteralCharacterClass('='))
            )
        rx.start()
        rx.feed('<')
        self.assertFalse(rx.isDeadEnd())

    def test_newline(self):
        rx = RegularExpression.fromClass(LitteralCharacterClass('\n'))
        self.assertTrue(rx.match('\n'))

    def test_class(self):
        rx = RegularExpression.fromClass(LitteralCharacterClass('a'))
        self.assertTrue(rx.match('a'))
        self.assertFalse(rx.match('b'))

    def test_concat(self):
        rx = RegularExpression.concat(
            RegularExpression.fromClass(LitteralCharacterClass('a')),
            RegularExpression.fromClass(LitteralCharacterClass('b')),
            RegularExpression.fromClass(LitteralCharacterClass('c'))
            )
        self.assertTrue(rx.match('abc'))
        self.assertFalse(rx.match('ab'))

    def test_union(self):
        rx = RegularExpression.union(
            RegularExpression.fromClass(LitteralCharacterClass('a')),
            RegularExpression.fromClass(LitteralCharacterClass('b')),
            RegularExpression.fromClass(LitteralCharacterClass('c'))
            )
        self.assertTrue(rx.match('a'))
        self.assertTrue(rx.match('b'))
        self.assertTrue(rx.match('c'))
        self.assertFalse(rx.match('d'))

    def test_kleene(self):
        rx = RegularExpression.kleene(RegularExpression.fromClass(LitteralCharacterClass('a')))
        self.assertTrue(rx.match(''))
        self.assertTrue(rx.match('a'))
        self.assertTrue(rx.match('aa'))
        self.assertFalse(rx.match('ab'))

    def test_exponent(self):
        rx = RegularExpression.exponent(RegularExpression.fromClass(LitteralCharacterClass('a')), 2, 3)
        self.assertFalse(rx.match('a'))
        self.assertTrue(rx.match('aa'))
        self.assertTrue(rx.match('aaa'))
        self.assertFalse(rx.match('aaaa'))

    def test_exponent_min(self):
        rx = RegularExpression.exponent(RegularExpression.fromClass(LitteralCharacterClass('a')), 2)
        self.assertFalse(rx.match('a'))
        self.assertTrue(rx.match('aa'))
        self.assertTrue(rx.match('aaa'))

    def test_exponent_null(self):
        rx = RegularExpression.exponent(RegularExpression.fromClass(LitteralCharacterClass('a')), 0, 1)
        self.assertTrue(rx.match(''))
        self.assertTrue(rx.match('a'))
        self.assertFalse(rx.match('aa'))


if __name__ == '__main__':
    unittest.main()
