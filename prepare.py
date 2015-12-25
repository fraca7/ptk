#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from ptk.meta import PackageInfo

def generateReadme():
    with open('README.rst.in', 'rb') as src:
        contents = src.read().decode('UTF-8')
        contents = contents % PackageInfo.__dict__
        with open('README.rst', 'wb') as dst:
            dst.write(contents.encode('UTF-8'))


def prepare():
    generateReadme()


if __name__ == '__main__':
    prepare()
