#!/bin/bash

# web app entry point

set -e

# Run database migrations
flask db upgrade
flask db migrate
flask create-admin admin admin@admin.com admin123

# Start the Flask development server
exec flask run --host=0.0.0.0 --port=80