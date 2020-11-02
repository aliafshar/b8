
run:
	python3 b8.py

lint:
	flake8

ve:
	virtualenv -p python3 --system-site-packages ve
	./ve/bin/pip install -I flit
	./ve/bin/flit install

sdist: clean
	flit build

clean:
	rm -rf build dist b8.egg-info ve __pycache__ b8/__pycache__

upload: sdist
	flit publish

release: upload
	make clean
	echo done

wwwreadme:
	tail -n+4 tools/www/src/index.md > README.md

wwwclean:
	rm -rf tools/www/public

wwwbuild:
	eleventy --config tools/www/eleventyconfig.js

wwwdeploy: wwwbuild
	cd tools/www && firebase deploy
