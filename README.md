pixywerk
========

A simple WSGI file-system-oriented CMS


running with gunicorn
---------------------

gunicorn -e "PIXYWERK_CONFIG=path/to/config.json" pixywerk.wsgi:do_werk
