#!/bin/bash
# seed_data.sh
# Inserta datos de ejemplo en la base

source .venv/bin/activate

echo "📌 Insertando datos de prueba..."
echo "
from backlog.models import Integrante, Sprint, Tarea
from django.contrib.auth.models import User
from datetime import date, timedelta

# Crear usuarios base
usuarios = [
    ('andres', 'Andrés'),
    ('diego', 'Diego'),
    ('daniela', 'Daniela'),
]

for username, nombre in usuarios:
    user, created = User.objects.get_or_create(username=username, defaults={'first_name': nombre})
    Integrante.objects.get_or_create(user=user, rol='Desarrollador')

# Crear sprint actual (una semana desde hoy)
inicio = date.today()
fin = inicio + timedelta(days=7)
sprint, _ = Sprint.objects.get_or_create(inicio=inicio, fin=fin)

# Crear tareas de prueba
Tarea.objects.get_or_create(
    titulo='Configurar servidor de desarrollo',
    categoria='UI',
    sprint=sprint,
    asignado_a=Integrante.objects.first()
)

Tarea.objects.get_or_create(
    titulo='Diseñar dashboard inicial',
    categoria='NUI',
    sprint=sprint,
    asignado_a=Integrante.objects.last()
)

print('✅ Datos de prueba insertados')
" | python manage.py shell

