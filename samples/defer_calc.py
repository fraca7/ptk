#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""

Four operations calculator, asynchronous (using Twisted). Due to
various buffering problems you probably won't see what's the point
unless you force stdin to be noninteractive, e.g.

$ echo '3*4+6' | python3 ./defer_calc.py

"""

import six, operator, os, sys, codecs

from ptk.deferred_lexer import token, DeferredLexer, EOF
from ptk.deferred_parser import production, leftAssoc, DeferredLRParser, ParseError

from twisted.internet.defer import succeed
from twisted.internet.protocol import Protocol
from twisted.internet import stdio, reactor


@leftAssoc('+', '-')
@leftAssoc('*', '/')
class Parser(DeferredLRParser, DeferredLexer):
    def deferNewSentence(self, result):
        six.print_('== Result:', result)
        return succeed(None)

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
        return -value # You can return something else than a Deferred.

    @production('E -> "(" E<value> ")"')
    def paren(self, value):
        return succeed(value)

    @production('E -> number<number>')
    def litteral(self, number):
        return succeed(number)

    @production('E -> E<left> "+"<op> E<right>')
    @production('E -> E<left> "-"<op> E<right>')
    @production('E -> E<left> "*"<op> E<right>')
    @production('E -> E<left> "/"<op> E<right>')
    def binaryop(self, left, op, right):
        six.print_('Binary operation: %s %s %s' % (left, op, right))
        return succeed({
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.floordiv
            }[op](left, right))


class BytesProtocol(Protocol):
    def __init__(self, *args, **kwargs):
        self.parser = Parser()
        self.decoder = codecs.getincrementaldecoder('utf_8')()

    def connectionLost(self, reason):
        six.print_('Connection lost: %s' % reason)
        reactor.stop()

    def dataReceived(self, data):
        # We don't want more bytes to be handled while this is running.
        self.transport.pauseProducing()

        bytes = list(data)
        def next(result):
            if bytes:
                char = self.decoder.decode(bytes.pop(0))
                if char:
                    if char == '\n':
                        char = EOF
                    else:
                        six.print_('Input char: "%s"' % repr(char))
                    self.parser.deferFeed(char).addCallbacks(next, self.error)
                else:
                    next(None)
            else:
                self.transport.resumeProducing()
        next(None)

    def error(self, reason):
        six.print_('ERROR: %s' % reason)


stdio.StandardIO(BytesProtocol())
reactor.run()
