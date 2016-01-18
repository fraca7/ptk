# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015
# See LICENSE.txt

import six


class PackageInfo(object):
    version = six.u('1.3.1')
    version_info = map(int, version.split(six.u('.')))

    project_name = six.u('ptk')
    project_url = six.u('https://bitbucket.org/fraca7/ptk')
    download_url = six.u('https://pypi.python.org/packages/source/p/ptk/ptk-%s.tar.gz') % version

    author_name = six.u('J\u00E9r\u00F4me Laheurte')
    author_email = six.u('jerome@jeromelaheurte.net')

    short_description = six.u('LR(1) parsing framework for Python with support for asynchronous input')


version = PackageInfo.version
version_info = PackageInfo.version_info
