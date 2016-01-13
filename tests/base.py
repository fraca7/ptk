#!/usr/bin/env python

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)-15s %(levelname)-8s %(name)-15s %(message)s')
