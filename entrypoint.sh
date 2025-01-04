#!/bin/sh

# Your series of commands
python manage.py collectstatic --clear
python manage.py collectstatic --noinput
# python manage.py spectacular --color --file schema.yml
python manage.py migrate
# exec /usr/local/bin/gunicorn config.asgi --bind 0.0.0.0:5000 --chdir=/app -k uvicorn.workers.UvicornWorker
# exec /usr/local/bin/gunicorn config.asgi --bind 0.0.0.0:5000 --chdir=/app
exec /usr/local/bin/gunicorn config.wsgi --bind 0.0.0.0:5000 --chdir=/app
# exec python manage.py runserver 0.0.0.0:5000
