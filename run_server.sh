#!/bin/bash
# run_server.sh
source .venv/bin/activate
echo "🚀 Levantando servidor en http://127.0.0.1:8000/"
python manage.py runserver

