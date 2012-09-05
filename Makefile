release:
	python setup.py register sdist bdist_dumb upload

gh-docs:
	git checkout gh-pages
	git checkout master README.rst conf.py
	sphinx-build . .
	git rm -f README.rst conf.py
	rm -rf _sources objects.inv .doctrees .buildinfo
	git add .
	git commit -a -m "Regenerate documentation for github" -e
	git checkout master
	git push origin gh-pages
