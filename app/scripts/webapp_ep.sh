#!/bin/bash

# web app entry point

set -e

# Run database migrations
flask db upgrade
flask db migrate
flask create-admin admin admin@admin.com admin123admin
flask create-admin admin2 admin2@admin2.com admin12321admin
flask create-bank zibal

# Start the Flask development server
exec flask run --host=0.0.0.0 --port=80