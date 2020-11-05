
run:
	python3 b8.py

lint:
	flake8

ve:
	virtualenv -p python3 --system-site-packages ve
	./ve/bin/pip install -I flit
	./ve/bin/flit install

clean:
	rm -rf build dist b8.egg-info ve __pycache__ b8/__pycache__ b8/*.pyc .pytype/

copytoml:
	cp dev/pyproject.toml .
	git add pyproject.toml

uncopytoml:
	git rm pyproject.toml

sdist:
	flit build

upload:
	flit publish

release: clean copytoml upload uncopytoml
	make clean
	echo done

wwwreadme:
	tail -n+4 dev/www/src/index.md > README.md

wwwclean:
	rm -rf dev/www/public

wwwbuild:
	eleventy --config dev/www/eleventyconfig.js

wwwdeploy: wwwbuild
	cd dev/www && firebase deploy
