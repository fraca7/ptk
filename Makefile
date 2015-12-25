
PYTHON?=python3
VERSION=$(shell $(PYTHON) -c 'from ptk.meta import version; import six; six.print_(version)')
FTPPWD=`grep FTPPWD ~/.ptkreleaserc | cut -f2 -d=`

all:
	@echo Targets:
	@echo   all:       This help
	@echo   prepare:   Refresh generated files
	@echo   unittests: All unit tests
	@echo   coverage:  Test coverage
	@echo   lint:      Pylint
	@echo   nuke:      Delete all unversioned files
	@echo   documentation: Documentation
	@echo   tarball:   Source distribution

prepare:
	$(PYTHON) ./prepare.py

unittests:
	$(PYTHON) tests/test_all.py

coverage:
	$(PYTHON) -m coverage run --branch --omit "tests/*,/usr/*" tests/test_all.py
	$(PYTHON) -m coverage html

lint:
	-$(PYTHON) -m pylint ptk > lint.html

nuke:
	hg purge --all

documentation:
	cd doc; make html
	rm -rf html
	cp -a doc/build/html .

tarball: documentation
	$(PYTHON) setup.py sdist --formats=bztar

release: tarball
	curl -T dist/ptk-$(VERSION).tar.bz2 ftp://jerome:$(FTPPWD)@192.168.1.2/ptk-web/downloads/ptk-$(VERSION).tar.bz2
