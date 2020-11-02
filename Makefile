
PYTHON?=python3

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
	-$(PYTHON) -m pylint ptk

nuke:
	git clean -dxf

documentation:
	cd doc; $(MAKE) html
	rm -rf html
	mv doc/build/html .

tarball: documentation
	$(PYTHON) setup.py sdist --formats=bztar

release: documentation
	python ./setup.py sdist upload -r pypi
