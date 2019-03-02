#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""

Four operations calculator, asynchronous. Due to various buffering
problems you probably won't see what's the point unless you force
stdin to be noninteractive, e.g.

$ echo '3*4+6' | python3 ./async_calc.py

"""

import operator, os, asyncio, sys, codecs

from ptk.async_lexer import token, AsyncLexer, EOF
from ptk.async_parser import production, leftAssoc, AsyncLRParser, ParseError


@leftAssoc('+', '-')
@leftAssoc('*', '/')
class Parser(AsyncLRParser, AsyncLexer):
    async def asyncNewSentence(self, result):
        print('== Result:', result)

    # Lexer
    def ignore(self, char):
        return char in [' ', '\t']

    @token(r'[1-9][0-9]*')
    def number(self, tok):
        tok.value = int(tok.value)

    # Parser

    @production('E -> "-" E<value>', priority='*')
    async def minus(self, value):
        print('== Neg: - %d' % value)
        return -value

    @production('E -> "(" E<value> ")"')
    async def paren(self, value):
        return value

    @production('E -> number<number>')
    async def litteral(self, number):
        return number

    @production('E -> E<left> "+"<op> E<right>')
    @production('E -> E<left> "-"<op> E<right>')
    @production('E -> E<left> "*"<op> E<right>')
    @production('E -> E<left> "/"<op> E<right>')
    async def binaryop(self, left, op, right):
        print('Binary operation: %s %s %s' % (left, op, right))
        return {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.floordiv
            }[op](left, right)


async def main():
    reader = asyncio.StreamReader()
    await asyncio.get_event_loop().connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    decoder = codecs.getincrementaldecoder('utf_8')()

    parser = Parser()

    while True:
        byte = await reader.read(1)
        if not byte:
            break
        char = decoder.decode(byte)
        if char:
            if char == '\n':
                char = EOF
            else:
                print('Input char: "%s"' % repr(char))
            await parser.asyncFeed(char)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
