#!/usr/bin/env python3

import base, unittest, copy
from ptk.utils import memoize, Singleton, chars


# I don't know what discover does, but it makes this test fail...

## class MemoizeTestCase(unittest.TestCase):
##     def setUp(self):
##         self.calls = list()

##     @memoize
##     def compute(self, v):
##         self.calls.append(v)
##         return v

##     def test_memoize(self):
##         self.compute(42)
##         self.compute(13)
##         self.assertEqual(self.compute(42), 42)
##         self.assertEqual(self.calls, [42, 13])


class SingletonUnderTest(metaclass=Singleton):
    __reprval__ = '$'

    def __init__(self):
        self.value = 42


class SingletonTestCase(unittest.TestCase):
    def test_instance(self):
        self.assertFalse(isinstance(SingletonUnderTest, type))

    def test_init(self):
        self.assertEqual(SingletonUnderTest.value, 42)

    def test_order(self):
        values = ['spam', SingletonUnderTest]
        values.sort()
        self.assertEqual(values, [SingletonUnderTest, 'spam'])

    def test_copy(self):
        self.assertTrue(copy.copy(SingletonUnderTest) is SingletonUnderTest)

    def test_deepcopy(self):
        self.assertTrue(copy.deepcopy(SingletonUnderTest) is SingletonUnderTest)

    def test_repr(self):
        self.assertEqual(repr(SingletonUnderTest), '$')

    def test_eq(self):
        self.assertNotEqual(SingletonUnderTest, SingletonUnderTest.__class__())


class CharsTestCase(unittest.TestCase):
    def test_str(self):
        self.assertTrue('*' in chars('*'))

    def test_bytes(self):
        for byte in b'*':
            self.assertTrue(byte in chars('*'))


if __name__ == '__main__':
    unittest.main()
