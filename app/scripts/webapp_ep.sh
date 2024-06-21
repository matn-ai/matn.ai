#!/bin/bash

# web app entry point

set -e

# Run database migrations
flask db upgrade
flask db migrate

# Start the Flask development server
exec flask run --host=0.0.0.0 --port=80