release:
	git push origin master
	python setup.py register sdist bdist_dumb upload

gh-docs: clean
	git checkout gh-pages
	git checkout master README.rst conf.py
	mv README.rst index.rst
	sphinx-build . .
	git rm -f README.rst conf.py
	rm -rf _sources objects.inv .doctrees .buildinfo index.rst
	git add .
	git commit -a -m "Regenerate documentation for github" -e
	git checkout master
	git push origin gh-pages

clean:
	rm -rf dist build MANIFEST
