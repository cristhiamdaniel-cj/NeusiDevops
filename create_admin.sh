#!/bin/bash
# create_admin.sh
# Crear un superusuario por defecto

source venv/bin/activate

echo "📌 Creando superusuario Django (usuario: neusi_admin / pass: Neusi123*)"
echo "from django.contrib.auth.models import User
if not User.objects.filter(username='neusi_admin').exists():
    User.objects.create_superuser('neusi_admin', 'admin@neusi.com', 'Neusi123*')
" | python manage.py shell

echo "✅ Superusuario creado."

