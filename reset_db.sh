#!/bin/bash
# reset_db.sh
source venv/bin/activate
echo "⚠️ Reseteando base de datos..."
rm db.sqlite3
rm -rf backlog/migrations
python manage.py makemigrations backlog
python manage.py migrate
echo "✅ Base de datos limpia."

