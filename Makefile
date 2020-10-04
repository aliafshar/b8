


dist: sdist clean

upload: dist
	twine upload dist/*


sdist: manifest
	python setup.py sdist

manifest:
	cp README.md README
	echo include LICENSE > MANIFEST.in

clean:
	rm -f MANIFEST MANIFEST.in README
