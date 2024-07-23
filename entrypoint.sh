#!/bin/sh

echo 'Waiting for postgres...'

while ! nc -z $DB_HOSTNAME $DB_PORT; do
    sleep 0.1
done

echo 'Running migrations...'
python manage.py makemigrations
python manage.py migrate

# Create a directory for collecting static files
RUN mkdir -p /code/staticfiles

# Set STATIC_ROOT environment variable to the newly created directory
ENV STATIC_ROOT /code/staticfiles

echo 'Collecting static files...'
python manage.py collectstatic --no-input

# Run app.py when the container launches
exec "$@"