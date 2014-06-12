#!/bin/sh
set -e

for i in farnsworth afro hoyt
do
	cd ../$i
	git pull
	./manage.py collectstatic --noinput
	./manage.py update_index
	./manage.py test
done
