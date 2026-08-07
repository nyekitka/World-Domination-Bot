#!/bin/sh
set -e

python web_app/manage.py collectstatic --noinput

exec "$@"