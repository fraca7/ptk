#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Converts a Yacc/Bison grammar definition into a Python skeleton that uses ptk.
"""

import getopt
import sys
import six
import collections
import codecs

from ptk.parser import production, LRParser, ParseError
from ptk.lexer import token, ReLexer, EOF


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
            six.print_('--compact and --arguments are not compatible')
            self.usage(1)

        if self.filename is None:
            six.print_('Output file not specified')
            self.usage(1)

    def usage(self, exitCode=0):
        six.print_('Usage: %s [options] filename' % sys.argv[0])
        six.print_('Options:')
        six.print_('  -h, --help      Print this')
        six.print_('  -c, --compact   Create one method for all alternatives of a production')
        six.print_('  -o, --output <filename> Output to file (mandatory)')
        six.print_('  -a, --arguments Generate argument names for items in productions (incompatible with --compact)')
        sys.exit(exitCode)

    @staticmethod
    def create():
        opts, args = getopt.getopt(sys.argv[1:], 'caho:', ['compact', 'arguments', 'help', 'output='])
        return Options(opts), args


class YaccParser(LRParser, ReLexer):
    def __init__(self, options, stream):
        self.stream = stream
        self.options = options
        super(YaccParser, self).__init__()

        self.state = 0
        self.yaccStartSymbol = None
        self.allTokens = list()
        self.allProductions = list()
        self.precedences = list()

    # Lexer

    @token(r'%\{', types=[])
    def c_decl(self, tok):
        class IgnoreCDecl(object):
            def __init__(self):
                self.state = 0
            def feed(self, char):
                if self.state == 0:
                    if char == '%':
                        self.state = 1
                elif self.state == 1:
                    if char == '}':
                        return None, None # Token type None -> ignored
                    elif char != '%':
                        self.state = 0
        self.setConsumer(IgnoreCDecl())

    @token(r'/\*', types=[])
    def comment(self, tok):
        class Comment(object):
            def __init__(self):
                self.state = 0
                self.value = six.StringIO()

            def feed(self, char):
                if self.state == 0:
                    if char == '*':
                        self.state = 1
                    else:
                        self.value.write(char)
                elif self.state == 1:
                    if char == '/':
                        return None, None # Ignore
                    elif char == '*':
                        self.value.write('*')
                    else:
                        self.value.write(char)
                        self.state = 0
        self.setConsumer(Comment())

    @token(r'%union\s*{', types=[]) # Hum, no LF possible before {
    def union(self, tok):
        class Union(object):
            def feed(self, char):
                if char == '}':
                    return None, None
        self.setConsumer(Union())

    @token(r'%%')
    def part_sep(self, tok):
        self.state += 1
        if self.state == 1:
            six.print_()
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

    @token(r'%token')
    def token_decl(self, tok):
        pass

    @token(r'%(left|right|nonassoc)')
    def assoc_decl(self, tok):
        pass

    @token(r'%prec')
    def prec_decl(self, tok):
        pass

    @token(r'%start')
    def start_decl(self, tok):
        pass

    @token(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def identifier(self, tok):
        pass

    @token(r'\{')
    def semantic_action(self, tok):
        # Don't try to be too smart; just balance {} that are not in string litterals
        class CSemanticAction(object):
            def __init__(self):
                self.state = 0
                self.count = 1
                self.value = six.StringIO()
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

    # Don't use META_DECLARATION* because it introduces reduce/reduce conflicts
    @production('YACC_FILE -> META_DECLARATION+ part_sep PRODUCTIONS_LIST')
    @production('YACC_FILE -> part_sep PRODUCTIONS_LIST')
    def yacc_file(self):
        pass

    # Tokens, start symbol, etc

    @production('META_DECLARATION -> token_decl identifier+<tokens>')
    def token_declaration(self, tokens):
        self.allTokens.extend(tokens)

    @production('META_DECLARATION -> assoc_decl<assoc> identifier+<tokens>')
    def assoc_declaration(self, assoc, tokens):
        self.precedences.append((assoc, tokens))

    @production('META_DECLARATION -> start_decl identifier<name>')
    def start_declaration(self, name):
        self.yaccStartSymbol = name

    # Productions; we assume there's always at least one

    @production('PRODUCTIONS_LIST -> identifier<left> ":" PRODUCTION_ALTERNATIVES_LIST<productions> ";"')
    @production('PRODUCTIONS_LIST -> PRODUCTIONS_LIST identifier<left> ":" PRODUCTION_ALTERNATIVES_LIST<productions> ";"')
    def productions_list(self, left, productions):
        self.allProductions.append((left, productions))
        return self.allProductions

    @production('PRODUCTION_ALTERNATIVES_LIST -> PRODUCTION_DECL<prod>')
    @production('PRODUCTION_ALTERNATIVES_LIST -> PRODUCTION_ALTERNATIVES_LIST<prodList> "|" PRODUCTION_DECL<prod>')
    def next_production(self, prod, prodList=None):
        prodList = [] if prodList is None else prodList
        prodList.append(prod)
        return prodList

    @production('PRODUCTION_DECL -> ') # Empty
    @production('PRODUCTION_DECL -> SYMBOL+<symbols>')
    def production_decl(self, symbols):
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

    @production('PRODUCTION_DECL -> PRODUCTION_DECL<prod> semantic_action<action>')
    def production_decl_action(self, prod, action):
        if prod['action'] is not None:
            raise RuntimeError('Duplicate semantic action "%s"' % action)
        prod['action'] = action
        return prod

    @production('PRODUCTION_DECL -> PRODUCTION_DECL<prod> prec_decl identifier<prec>')
    def production_decl_prec(self, prod, prec):
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
                six.print_('Parse error: %s' % exc)
                tokens = exc.expecting()
                if tokens:
                    six.print_('Was expecting %s' % ', '.join(map(repr, sorted(tokens))))
                sys.exit(1)
            finally:
                print('== Parsed file in %d ms.' % int(1000 * (time.time() - t0)))


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.WARNING, format='%(asctime)-15s %(levelname)-8s %(name)-15s %(message)s')

    import sys
    main(sys.argv[1])
