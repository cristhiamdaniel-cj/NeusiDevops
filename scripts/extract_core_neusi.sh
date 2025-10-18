#!/bin/bash
# ==========================================================
# Script: extract_core_neusi.sh
# Objetivo: Extraer el core del monolito Django y preparar la versión 1.1
# Autor: Daniel Campos – NEUSI Solutions
# Fecha: Octubre 2025
# ==========================================================

# CONFIGURACIÓN GENERAL
BASE_DIR="/home/desarrollo/NeuralWasi/NeusiDevops"
PROJECT_NAME="neusitaskmanager"
NEW_VERSION="v1_1"
NEW_DIR="${BASE_DIR}/${PROJECT_NAME}_${NEW_VERSION}"
PG_DB="neusitaskmanager_db"
PG_USER="postgres"
PG_PASS="Alejito10."
PG_HOST="localhost"
PG_PORT="5432"

echo "🚀 Iniciando extracción del core de ${PROJECT_NAME}..."
sleep 1

# 1️⃣ Crear carpeta de nueva versión
mkdir -p "${NEW_DIR}"
cd "${BASE_DIR}" || exit

# 2️⃣ Copiar módulos principales del monolito
echo "📦 Copiando estructura principal..."
rsync -av --progress "${BASE_DIR}/${PROJECT_NAME}/" "${NEW_DIR}/" \
  --exclude='__pycache__' \
  --exclude='*.sqlite3' \
  --exclude='*.log' \
  --exclude='venv' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='.idea'

# 3️⃣ Limpiar migraciones viejas
echo "🧹 Limpiando migraciones antiguas..."
find "${NEW_DIR}" -path "*/migrations/*.py" ! -name "__init__.py" -delete

# 4️⃣ Crear entorno virtual
echo "🐍 Creando entorno virtual..."
cd "${NEW_DIR}" || exit
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

if [ -f requirements.txt ]; then
    echo "📥 Instalando dependencias..."
    pip install -r requirements.txt
else
    echo "⚠️ No se encontró requirements.txt, instalando Django..."
    pip install django psycopg2-binary djangorestframework
fi

# 5️⃣ Configurar base de datos PostgreSQL en settings.py
echo "⚙️ Configurando PostgreSQL en settings.py..."
SETTINGS_FILE=$(find "${NEW_DIR}" -name "settings.py" | head -n 1)

# Reemplazar bloque DATABASES
sed -i '/DATABASES = {/,$d' "$SETTINGS_FILE"
cat <<EOT >> "$SETTINGS_FILE"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${PG_DB}',
        'USER': '${PG_USER}',
        'PASSWORD': '${PG_PASS}',
        'HOST': '${PG_HOST}',
        'PORT': '${PG_PORT}',
    }
}
EOT

# 6️⃣ Crear base de datos PostgreSQL (si no existe)
echo "🗄️ Creando base de datos PostgreSQL si no existe..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE ${PG_DB};"

# 7️⃣ Aplicar migraciones iniciales
echo "🧱 Aplicando migraciones..."
python manage.py makemigrations
python manage.py migrate

# 8️⃣ Crear superusuario de prueba
echo "👤 Creando superusuario admin..."
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin','admin@neusi.com','12345')" | python manage.py shell

# 9️⃣ Verificación final
echo "✅ Extracción completada exitosamente"
echo "📂 Nueva versión creada: ${NEW_DIR}"
echo "🌐 Para iniciar el servidor ejecuta:"
echo "cd ${NEW_DIR} && source venv/bin/activate && python manage.py runserver 0.0.0.0:8000"
#!/bin/bash
# ==========================================================
# Script: extract_core_neusi.sh
# Objetivo: Extraer el core del monolito Django y preparar la versión 1.1
# Autor: Daniel Campos – NEUSI Solutions
# Fecha: Octubre 2025
# ==========================================================

# CONFIGURACIÓN GENERAL
BASE_DIR="/home/desarrollo/NeuralWasi/NeusiDevops"
PROJECT_NAME="neusitaskmanager"
NEW_VERSION="v1_1"
NEW_DIR="${BASE_DIR}/${PROJECT_NAME}_${NEW_VERSION}"
PG_DB="neusitaskmanager_db"
PG_USER="postgres"
PG_PASS="Alejito10."
PG_HOST="localhost"
PG_PORT="5432"

echo "🚀 Iniciando extracción del core de ${PROJECT_NAME}..."
sleep 1

# 1️⃣ Crear carpeta de nueva versión
mkdir -p "${NEW_DIR}"
cd "${BASE_DIR}" || exit

# 2️⃣ Copiar módulos principales del monolito
echo "📦 Copiando estructura principal..."
rsync -av --progress "${BASE_DIR}/${PROJECT_NAME}/" "${NEW_DIR}/" \
  --exclude='__pycache__' \
  --exclude='*.sqlite3' \
  --exclude='*.log' \
  --exclude='venv' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='.idea'

# 3️⃣ Limpiar migraciones viejas
echo "🧹 Limpiando migraciones antiguas..."
find "${NEW_DIR}" -path "*/migrations/*.py" ! -name "__init__.py" -delete

# 4️⃣ Crear entorno virtual
echo "🐍 Creando entorno virtual..."
cd "${NEW_DIR}" || exit
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

if [ -f requirements.txt ]; then
    echo "📥 Instalando dependencias..."
    pip install -r requirements.txt
else
    echo "⚠️ No se encontró requirements.txt, instalando Django..."
    pip install django psycopg2-binary djangorestframework
fi

# 5️⃣ Configurar base de datos PostgreSQL en settings.py
echo "⚙️ Configurando PostgreSQL en settings.py..."
SETTINGS_FILE=$(find "${NEW_DIR}" -name "settings.py" | head -n 1)

# Reemplazar bloque DATABASES
sed -i '/DATABASES = {/,$d' "$SETTINGS_FILE"
cat <<EOT >> "$SETTINGS_FILE"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${PG_DB}',
        'USER': '${PG_USER}',
        'PASSWORD': '${PG_PASS}',
        'HOST': '${PG_HOST}',
        'PORT': '${PG_PORT}',
    }
}
EOT

# 6️⃣ Crear base de datos PostgreSQL (si no existe)
echo "🗄️ Creando base de datos PostgreSQL si no existe..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1 || \
sudo -u postgres psql -c "CREATE DATABASE ${PG_DB};"

# 7️⃣ Aplicar migraciones iniciales
echo "🧱 Aplicando migraciones..."
python manage.py makemigrations
python manage.py migrate

# 8️⃣ Crear superusuario de prueba
echo "👤 Creando superusuario admin..."
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin','admin@neusi.com','12345')" | python manage.py shell

# 9️⃣ Verificación final
echo "✅ Extracción completada exitosamente"
echo "📂 Nueva versión creada: ${NEW_DIR}"
echo "🌐 Para iniciar el servidor ejecuta:"
echo "cd ${NEW_DIR} && source venv/bin/activate && python manage.py runserver 0.0.0.0:8000"

