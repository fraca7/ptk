#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Converts a Yacc/Bison grammar definition into a Python skeleton that uses ptk.
"""

import io
import getopt
import sys
import collections
import codecs
import re

from ptk.parser import production, LRParser, ParseError
from ptk.lexer import token, ReLexer, EOF
from ptk.regex import buildRegex, DeadState


Symbol = collections.namedtuple('Symbol', ('name', 'argname'))


class Options(object):
    def __init__(self, opts):
        self.compact = False
        self.arguments = False
        self.filename = None
        for opt, val in opts:
            if opt in ('-c', '--compact'):
                self.compact = True
            if opt in ('-a', '--arguments'):
                self.arguments = True
            if opt in ('-o', '--output'):
                self.filename = val
            if opt in ('-h', '--help'):
                self.usage()

        if self.compact and self.arguments:
            print('--compact and --arguments are not compatible')
            self.usage(1)

        if self.filename is None:
            print('Output file not specified')
            self.usage(1)

    def usage(self, exitCode=0):
        print('Usage: %s [options] filename' % sys.argv[0])
        print('Options:')
        print('  -h, --help      Print this')
        print('  -c, --compact   Create one method for all alternatives of a production')
        print('  -o, --output <filename> Output to file (mandatory)')
        print('  -a, --arguments Generate argument names for items in productions (incompatible with --compact)')
        sys.exit(exitCode)

    @staticmethod
    def create():
        opts, args = getopt.getopt(sys.argv[1:], 'caho:', ['compact', 'arguments', 'help', 'output='])
        return Options(opts), args


class NullToken(object):
    def __init__(self, endMarker):
        self.__rx = buildRegex('(.|\n)*%s' % re.escape(endMarker)).start()

    def feed(self, char):
        try:
            if self.__rx.feed(char):
                return None, None
        except DeadState:
            return None, None


class YaccParser(LRParser, ReLexer):
    def __init__(self, options, stream):
        self.stream = stream
        self.options = options
        super().__init__()

        self.state = 0
        self.yaccStartSymbol = None
        self.allTokens = list()
        self.allProductions = list()
        self.precedences = list()

    # Lexer

    @token(r'%\{', types=[])
    def c_decl(self, tok):
        self.setConsumer(NullToken('%}'))

    @token(r'/\*', types=[])
    def comment(self, tok):
        self.setConsumer(NullToken('*/'))

    @token(r'%union\s*{', types=[]) # Hum, no LF possible before {
    def union(self, tok):
        self.setConsumer(NullToken('}'))

    @token(r'%%')
    def part_sep(self, tok):
        self.state += 1
        if self.state == 2:
            # Ignore C code after last %%
            class IgnoreCCode(object):
                def feed(self, char):
                    if char is EOF:
                        return EOF, EOF
            self.setConsumer(IgnoreCCode())

    @staticmethod
    def ignore(char):
        return char in [' ', '\t', '\n']

    @token(r'%(left|right|nonassoc)')
    def assoc_decl(self, tok):
        pass

    @token(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def identifier(self, tok):
        pass

    @token('[1-9][0-9]*')
    def number(self, tok):
        tok.value = int(tok.value)

    @token('"')
    def string(self, tok):
        class StringParser(object):
            def __init__(self):
                self.state = 0
                self.value = io.StringIO()
            def feed(self, char):
                if self.state == 0:
                    if char == '"':
                        return 'string', self.value.getvalue()
                    if char == '\\':
                        self.state = 1
                    else:
                        self.value.write(char)
                elif self.state == 1:
                    self.value.write(char)
                    self.state = 0
        self.setConsumer(StringParser())

    @token(r'\{')
    def semantic_action(self, tok):
        # Don't try to be too smart; just balance {} that are not in string litterals
        class CSemanticAction(object):
            def __init__(self):
                self.state = 0
                self.count = 1
                self.value = io.StringIO()
                self.value.write('{')

            def feed(self, char):
                self.value.write(char)
                if self.state == 0: # Nothing special
                    if char == '}':
                        self.count -= 1
                        if self.count == 0:
                            return 'semantic_action', self.value.getvalue()
                    elif char == '{':
                        self.count += 1
                    elif char == '\\':
                        self.state = 1
                    elif char == '\'':
                        self.state = 2
                    elif char == '"':
                        self.state = 4
                elif self.state == 1: # Escaping single char
                    self.state = 0
                elif self.state == 2: # Character litteral. Not that this accepts several characters
                    if char == '\\':
                        self.state = 3
                    elif char == '\'':
                        self.state = 0
                elif self.state == 3: # Escaping in character litteral
                    self.state = 2
                elif self.state == 4: # In string litteral
                    if char == '\\':
                        self.state = 5
                    elif char == '"':
                        self.state = 0
                elif self.state == 5: # Escaping in string litteral
                    self.state = 4
        self.setConsumer(CSemanticAction())

    @token(r'\'.\'')
    def litteral_token(self, tok):
        tok.value = tok.value[1]

    # Parser

    @production('YACC_FILE -> META_DECLARATION* part_sep PRODUCTION_DECL*')
    def yacc_file(self):
        pass

    # Tokens, start symbol, etc

    @production('META_DECLARATION -> "%token" identifier+<tokens>')
    def token_declaration(self, tokens):
        self.allTokens.extend(tokens)

    @production('META_DECLARATION -> assoc_decl<assoc> identifier+<tokens>')
    def assoc_declaration(self, assoc, tokens):
        self.precedences.append((assoc, tokens))

    @production('META_DECLARATION -> "%start" identifier<name>')
    def start_declaration(self, name):
        self.yaccStartSymbol = name

    @production('META_DECLARATION -> "%type" identifier identifier+')
    @production('META_DECLARATION -> "%expect" number')
    @production('META_DECLARATION -> "%debug"')
    @production('META_DECLARATION -> "%defines"')
    @production('META_DECLARATION -> "%destructor" semantic_action identifier+')
    @production('META_DECLARATION -> "%file-prefix" "=" string')
    @production('META_DECLARATION -> "%locations"')
    @production('META_DECLARATION -> "%name-prefix" "=" string')
    @production('META_DECLARATION -> "%no-parser')
    @production('META_DECLARATION -> "%no-lines')
    @production('META_DECLARATION -> "%output" "=" string')
    @production('META_DECLARATION -> "%pure-parser"')
    @production('META_DECLARATION -> "%token-table"')
    @production('META_DECLARATION -> "%verbose"')
    @production('META_DECLARATION -> "%yacc"')
    def ignored_declaration(self):
        pass

    # Productions

    @production('PRODUCTION_DECL -> identifier<left> ":" PRODUCTION_RIGHT+("|")<right> ";"')
    def production_decl(self, left, right):
        self.allProductions.append((left, right))

    @production('PRODUCTION_RIGHT -> SYMBOL*<symbols>')
    def production_right(self, symbols):
        names = list()
        indexes = dict()
        for symbol in symbols:
            if symbol.argname is None:
                names.append((symbol.name, None))
            else:
                index = indexes.get(symbol.argname, 0)
                argname = symbol.argname if index == 0 else '%s_%d' % (symbol.argname, index + 1)
                indexes[symbol.argname] = index + 1
                names.append((symbol.name, argname))

        return dict(names=names, action=None, precedence=None)

    @production('PRODUCTION_RIGHT -> PRODUCTION_RIGHT<prod> semantic_action<action>')
    def production_right_action(self, prod, action):
        if prod['action'] is not None:
            raise RuntimeError('Duplicate semantic action "%s"' % action)
        prod['action'] = action
        return prod

    @production('PRODUCTION_RIGHT -> PRODUCTION_RIGHT<prod> "%prec" identifier<prec>')
    def production_right_prec(self, prod, prec):
        if prod['precedence'] is not None:
            raise RuntimeError('Duplicate precedence declaration "%s"' % prec)
        prod['precedence'] = prec
        return prod

    @production('SYMBOL -> identifier<tok>')
    def symbol_from_identifier(self, tok):
        return Symbol(tok, None if tok in self.allTokens else tok)

    @production('SYMBOL -> litteral_token<tok>')
    def symbol_from_litteral(self, tok):
        return Symbol('"%s"' % tok, None)

    def newSentence(self, result):
        self.stream.write('from ptk.lexer import ReLexer, token\n')
        self.stream.write('from ptk.parser import LRParser, production, leftAssoc, rightAssoc, nonAssoc\n')
        self.stream.write('\n')

        for assocType, tokens in self.precedences:
            self.stream.write('@%s(%s)\n' % ({'%left': 'leftAssoc', '%right': 'rightAssoc', '%nonassoc': 'nonAssoc'}[assocType],
                                             ', '.join([repr(tok) for tok in tokens])))
        self.stream.write('class Parser(LRParser, ReLexer):\n')
        if self.yaccStartSymbol is not None:
            self.stream.write('    startSymbol = %s\n' % repr(self.yaccStartSymbol))
            self.stream.write('\n')

        self.stream.write('    # Lexer\n')
        for name in self.allTokens:
            self.stream.write('\n')
            self.stream.write('    @token(r\'\')\n')
            self.stream.write('    def %s(self, tok):\n' % name)
            self.stream.write('        pass\n')

        methodIndexes = dict()
        def methodName(name):
            index = methodIndexes.get(name, 0)
            methodIndexes[name] = index + 1
            return name if index == 0 else '%s_%d' % (name, index + 1)

        for name, prods in self.allProductions:
            for prod in prods:
                if not self.options.compact:
                    self.stream.write('\n')
                if prod['action'] is not None:
                    for line in prod['action'].split('\n'):
                        self.stream.write('    # %s\n' % line)
                symnames = []
                for aname, argname in prod['names']:
                    symnames.append(aname if argname is None or not self.options.arguments else '%s<%s>' % (aname, argname))
                self.stream.write('    @production(\'%s -> %s\'' % (name, ' '.join(symnames)))
                if prod['precedence'] is not None:
                    self.stream.write(', priority=%s' % repr(prod['precedence']))
                self.stream.write(')\n')
                if not self.options.compact:
                    self.stream.write('    def %s(self' % methodName(name))
                    if self.options.arguments:
                        for aname, argname in prod['names']:
                            if argname is not None:
                                self.stream.write(', %s' % argname)
                    self.stream.write('):\n')
                    self.stream.write('        pass\n')
            if self.options.compact:
                self.stream.write('    def %s(self):\n' % methodName(name))
                self.stream.write('        pass\n')
                self.stream.write('\n')


def main(filename):
    import time
    options, filenames = Options.create()
    for filename in filenames:
        with codecs.getreader('utf_8')(open(filename, 'rb')) as fileobj:
            output = sys.stdout if options.filename == '-' else codecs.getwriter('utf_8')(open(options.filename, 'wb'))
            parser = YaccParser(options, output)
            t0 = time.time()
            try:
                parser.parse(fileobj.read())
            except ParseError as exc:
                print('Parse error: %s' % exc)
                tokens = exc.expecting()
                if tokens:
                    print('Was expecting %s' % ', '.join(map(repr, sorted(tokens))))
                sys.exit(1)
            finally:
                print('== Parsed file in %d ms.' % int(1000 * (time.time() - t0)))


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARNING, format='%(asctime)-15s %(levelname)-8s %(name)-15s %(message)s')

    import sys
    main(sys.argv[1])
