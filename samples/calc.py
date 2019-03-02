#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Simple four operations calculator.
"""

import operator

from ptk.lexer import ReLexer, token
from ptk.parser import LRParser, leftAssoc, production, ParseError


@leftAssoc('+', '-')
@leftAssoc('*', '/')
class SimpleCalc(LRParser, ReLexer):
    def newSentence(self, result):
        print('== Result:', result)

    # Lexer
    def ignore(self, char):
        return char in [' ', '\t']

    @token(r'[1-9][0-9]*')
    def number(self, tok):
        tok.value = int(tok.value)

    # Parser

    @production('E -> "-" E<value>', priority='*')
    def minus(self, value):
        print('== Neg: - %d' % value)
        return -value

    @production('E -> "(" E<value> ")"')
    def paren(self, value):
        return value

    @production('E -> number<number>')
    def litteral(self, number):
        return number

    @production('E -> E<left> "+"<op> E<right>')
    @production('E -> E<left> "-"<op> E<right>')
    @production('E -> E<left> "*"<op> E<right>')
    @production('E -> E<left> "/"<op> E<right>')
    def binaryop(self, left, op, right):
        print('Binary operation: %s %s %s' % (left, op, right))
        return {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.floordiv
            }[op](left, right)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARNING, format='%(asctime)-15s %(levelname)-8s %(name)-15s %(message)s')

    print('Enter an arithmetic expression.')

    parser = SimpleCalc()
    while True:
        try:
            line = input('> ')
        except (KeyboardInterrupt, EOFError):
            print()
            break
        try:
            parser.parse(line)
        except ParseError as exc:
            print('Parse error: %s' % exc)
            print('Expected %s' % exc.expecting())
