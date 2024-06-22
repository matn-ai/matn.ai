#!/bin/bash

# web app entry point

set -e


# Start the Flask development server
exec celery -A app.tasks worker --loglevel=info