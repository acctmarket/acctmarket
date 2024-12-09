#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# Configure DATABASE_URL if environment variables are provided
if [ -z "${POSTGRES_USER:-}" ]; then
    base_postgres_image_default_user='postgres'
    export POSTGRES_USER="${base_postgres_image_default_user}"
fi

export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# Wait for PostgreSQL to be ready
wait-for-it "${POSTGRES_HOST}:${POSTGRES_PORT}" -t 30

>&2 echo 'PostgreSQL is available'

# Run Django management commands
python manage.py collectstatic --noinput
python manage.py spectacular --color --file schema.yml
python manage.py migrate

# Start the server
exec python manage.py runserver 0.0.0.0:5000
