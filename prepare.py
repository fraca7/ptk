#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import codecs

from ptk.meta import PackageInfo

def generateReadme():
    with codecs.getreader('utf-8')(open('README.rst.in', 'rb')) as src:
        contents = src.read()
        contents = contents % PackageInfo.__dict__
        with codecs.getwriter('utf-8')(open('README.rst', 'wb')) as dst:
            dst.write(contents)


def prepare():
    generateReadme()


if __name__ == '__main__':
    prepare()
