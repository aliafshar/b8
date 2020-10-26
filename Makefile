
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
	rm -rf build dist b8.egg-info ve __pycache__

upload: sdist
	flit release

release: upload
	make clean
	echo done

