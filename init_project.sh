#!/bin/bash
# init_project.sh
# Script para inicializar el proyecto Django de NEUSI

set -e

echo "🚀 Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Instalando dependencias..."
pip install --upgrade pip
pip install django

echo "📂 Creando proyecto Django..."
django-admin startproject neusi_tasks .

echo "📂 Creando app backlog..."
python manage.py startapp backlog

echo "⚙️ Registrando app en settings.py..."
sed -i "/INSTALLED_APPS = \[/a\ \ \ \ 'backlog'," neusi_tasks/settings.py

echo "🛠️ Aplicando migraciones iniciales..."
python manage.py migrate

echo "✅ Proyecto creado exitosamente."
echo "Para correr el servidor: ./run_server.sh"


