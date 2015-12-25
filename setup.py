# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015
# See LICENSE.txt

import six
from distutils.core import setup
from ptk.meta import version, PackageInfo

setup(
    name=six.u('ptk'),
    packages=['ptk'],
    version=version,
    description=PackageInfo.short_description,
    author=PackageInfo.author_name,
    author_email=PackageInfo.author_email,
    url=PackageInfo.project_url,
    download_url=PackageInfo.download_url,
    keywords=six.u('parser parsing compiler lr slr').split(),
    classifiers=[
      six.u('Development Status :: 5 - Production/Stable'),
      six.u('Intended Audience :: Developers'),
      six.u('License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)'),
      six.u('Operating System :: OS Independent'),
      six.u('Programming Language :: Python'),
      six.u('Topic :: Software Development :: Compilers'),
      six.u('Topic :: Software Development :: Libraries :: Python Modules'),
    ],
    install_requires=['six']
    )
