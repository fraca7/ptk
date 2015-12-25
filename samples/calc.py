#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Simple four operations calculator.
"""

import six, operator

from ptk.lexer import ReLexer, token
from ptk.parser import LRParser, leftAssoc, production, ParseError


@leftAssoc('+', '-')
@leftAssoc('*', '/')
class SimpleCalc(LRParser, ReLexer):
    def newSentence(self, result):
        six.print_('== Result:', result)

    # Lexer
    def ignore(self, char):
        return char in [' ', '\t']

    @token(r'[1-9][0-9]*')
    def number(self, tok):
        tok.value = int(tok.value)

    # Parser

    @production('E -> "-" E<value>', priority='*')
    def minus(self, value):
        six.print_('== Neg: - %d' % value)
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
        six.print_('Binary operation: %s %s %s' % (left, op, right))
        return {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.floordiv
            }[op](left, right)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARNING, format='%(asctime)-15s %(levelname)-8s %(name)-15s %(message)s')

    six.print_('Enter an arithmetic expression.')

    parser = SimpleCalc()
    while True:
        try:
            line = six.moves.input('> ')
        except (KeyboardInterrupt, EOFError):
            six.print_()
            break
        try:
            parser.parse(line)
        except ParseError as exc:
            six.print_('Parse error: %s' % exc)
            six.print_('Expected %s' % exc.expecting())
