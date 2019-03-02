#!/usr/bin/env python3

import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from test_utils import *
from test_regex import *
from test_regex_tokenizer import *
from test_regex_parser import *
from test_lexer import *
from test_grammar import *
from test_parser import *

try:
    import twisted
except ImportError:
    pass
else:
    from test_deferred_lexer import *
    from test_deferred_parser import *


if __name__ == '__main__':
    unittest.main()
