
run:
	python3 b8.py

lint:
	flake8

ve:
	virtualenv -p python3 --system-site-packages ve

sdist: clean ve
	./ve/bin/python setup.py sdist bdist_wheel

clean:
	rm -rf build dist b8.egg-info ve __pycache__

upload: sdist
	twine upload dist/*

release: upload
	make clean
	echo done

