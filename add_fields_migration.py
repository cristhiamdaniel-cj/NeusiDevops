# add_fields_migration.py
# Ejecutar con: python manage.py shell < add_fields_migration.py

from django.core.management import execute_from_command_line
import sys

print("🔄 Creando migración para nuevos campos...")
execute_from_command_line(['manage.py', 'makemigrations', 'backlog'])

print("🔄 Aplicando migraciones...")
execute_from_command_line(['manage.py', 'migrate'])

print("✅ Migraciones completadas.")