#!/usr/bin/env python3

import base, unittest

from ptk.grammar import Production, GrammarError, Grammar, production
from ptk.lexer import token
from ptk.parser import ProductionParser
from ptk.utils import callbackByName


class GrammarUnderTest(Grammar):
    tokens = set()

    @classmethod
    def addTokenType(cls, name, callback, regex, types=None):
        if types is None:
            cls.tokens.add(name)
        else:
            for name in types:
                cls.tokens.add(name)

    @classmethod
    def tokenTypes(cls):
        return cls.tokens

    @classmethod
    def _createProductionParser(cls, name, priority, attrs):
        return ProductionParser(callbackByName(name), priority, cls, attrs)


class ProductionParserTestCase(unittest.TestCase):
    def setUp(self):
        class TestGrammar(GrammarUnderTest):
            tokens = set()
        self.parser = ProductionParser(None, None, TestGrammar, dict())
        self.grammarClass = TestGrammar

    def assertHasProduction(self, prods, prod):
        for aProduction in prods:
            if prod == (aProduction.name, aProduction.right):
                return
        self.fail('Production %s not found in %s' % (prod, prods))

    def _parse(self, string):
        self.parser.parse(string)
        return self.grammarClass.productions()

    def test_production_name(self):
        prod, = self._parse('test -> A')
        self.assertEqual(prod.name, 'test')

    def test_production_callback(self):
        prod, = self._parse('test -> A')
        self.assertEqual(prod.callback, None)

    def test_empty_production(self):
        prod, = self._parse('test -> ')
        self.assertEqual(prod.right, [])

    def test_empty_end(self):
        prod1, prod2 = self._parse('test -> A | ')
        self.assertEqual(prod1.right, ['A'])
        self.assertEqual(prod2.right, [])

    def test_empty_start(self):
        prod1, prod2 = self._parse('test -> | A')
        self.assertEqual(prod1.right, [])
        self.assertEqual(prod2.right, ['A'])

    def test_order(self):
        prod, = self._parse('test -> A B')
        self.assertEqual(prod.right, ['A', 'B'])

    def test_escape_litteral(self):
        prod, = self._parse(r'test -> "spam\"foo"')
        self.assertEqual(prod.right, [r'spam"foo'])

    def _findListSym(self, prods):
        for prod in prods:
            if prod.name != 'test':
                return prod.name
        self.fail('Cannot find list symbol in %s' % repr(prods))

    def test_list(self):
        prods = self._parse('test -> A* "+"')
        self.assertEqual(len(prods), 4, repr(prods))
        listSym = self._findListSym(prods)

        self.assertHasProduction(prods, ('test', ['+']))
        self.assertHasProduction(prods, (listSym, ['A']))
        self.assertHasProduction(prods, (listSym, [listSym, 'A']))
        self.assertHasProduction(prods, ('test', [listSym, '+']))

    def test_list_not_empty(self):
        prods = self._parse('test -> A+')
        listSym = self._findListSym(prods)
        self.assertEqual(len(prods), 3, repr(prods))

        self.assertHasProduction(prods, (listSym, ['A']))
        self.assertHasProduction(prods, (listSym, [listSym, 'A']))
        self.assertHasProduction(prods, ('test', [listSym]))

    def test_list_with_separator(self):
        prods = self._parse('test -> A+(pipe)')
        self.assertEqual(len(prods), 3, repr(prods))
        listSym = self._findListSym(prods)

        self.assertHasProduction(prods, (listSym, ['A']))
        self.assertHasProduction(prods, (listSym, [listSym, 'pipe', 'A']))
        self.assertHasProduction(prods, ('test', [listSym]))

    def test_list_with_litteral_separator(self):
        prods = self._parse('test -> A+("|")')
        self.assertEqual(len(prods), 3, repr(prods))
        listSym = self._findListSym(prods)

        self.assertHasProduction(prods, (listSym, ['A']))
        self.assertHasProduction(prods, (listSym, [listSym, '|', 'A']))
        self.assertHasProduction(prods, ('test', [listSym]))

    def test_atmostone(self):
        prods = self._parse('test -> A?')
        self.assertEqual(len(prods), 2)
        self.assertHasProduction(prods, ('test', []))
        self.assertHasProduction(prods, ('test', ['A']))


class ProductionTestCase(unittest.TestCase):
    def setUp(self):
        # A -> B<b> C
        self.production = Production('A', self.callback)
        self.production.addSymbol('B', 'b')
        self.production.addSymbol('C')
        self.calls = list()

    def callback(self, grammar, **kwargs):
        self.calls.append(kwargs)
        return 42

    def test_duplicate(self):
        try:
            self.production.addSymbol('D', 'b')
        except GrammarError:
            pass
        else:
            self.fail()

    def test_kwargs(self):
        cb, kwargs = self.production.apply([1, 2], None)
        cb(self, **kwargs)
        self.assertEqual(self.calls, [{'b': 1}])


class GrammarTestCase(unittest.TestCase):
    def test_production(self):
        class G(GrammarUnderTest):
            @production('A -> B')
            def a(self):
                pass
        prod, = G.productions()
        self.assertEqual(prod.name, 'A')
        self.assertEqual(prod.right, ['B'])

    def test_start_symbol(self):
        class G(GrammarUnderTest):
            @production('A -> B')
            def a(self):
                pass
            @production('C -> D')
            def c(self):
                pass

        grammar = G()
        self.assertEqual(grammar.startSymbol, 'A')

    def test_duplicate_name(self):
        class G(GrammarUnderTest):
            @production('A -> B')
            def a1(self):
                pass
            @production('A -> C')
            def a2(self):
                pass
        prod1, prod2 = G.productions()
        self.assertEqual(prod1.name, 'A')
        self.assertEqual(prod1.right, ['B'])
        self.assertEqual(prod2.name, 'A')
        self.assertEqual(prod2.right, ['C'])

    def test_token_name(self):
        try:
            class G(GrammarUnderTest):
                tokens = set(['spam'])
                @production('spam -> spam')
                def spam(self):
                    pass
        except GrammarError:
            pass
        else:
            self.fail()

    def test_duplicate_production_1(self):
        class G(GrammarUnderTest):
            @production('A -> B|B')
            def a(self):
                pass

        try:
            G()
        except GrammarError:
            pass
        else:
            self.fail()

    def test_duplicate_production_2(self):
        class G(GrammarUnderTest):
            @production('A -> B')
            def a1(self):
                pass
            @production('A -> B')
            def a2(self):
                pass

        try:
            G()
        except GrammarError:
            pass
        else:
            self.fail()


if __name__ == '__main__':
    unittest.main()
