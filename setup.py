# -*- coding: UTF-8 -*-

# (c) Jérôme Laheurte 2015-2019
# See LICENSE.txt

from distutils.core import setup
from ptk.meta import version, PackageInfo

setup(
    name='ptk',
    packages=['ptk'],
    version=version,
    description=PackageInfo.short_description,
    author=PackageInfo.author_name,
    author_email=PackageInfo.author_email,
    url=PackageInfo.project_url,
    download_url=PackageInfo.download_url,
    keywords='parser parsing compiler lr slr'.split(),
    classifiers=[
      'Development Status :: 5 - Production/Stable',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
      'Topic :: Software Development :: Compilers',
      'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    )
