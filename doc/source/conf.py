# -*- coding: utf-8 -*-

import sys
import os
import shlex
import six

from ptk.meta import version, PackageInfo

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = PackageInfo.project_name
copyright = six.u('2015, %s') % PackageInfo.author_name
author = PackageInfo.author_name
release = version
language = None
exclude_patterns = []
pygments_style = 'sphinx'
todo_include_todos = False

html_theme = 'alabaster'
html_static_path = ['_static']
htmlhelp_basename = six.u('{name}doc').format(name=author)
