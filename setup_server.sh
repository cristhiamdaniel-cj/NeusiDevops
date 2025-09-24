#!/bin/bash
# setup_server.sh - Configuración NEUSI Task Manager (sin Docker)

echo "🚀 Configurando NEUSI Task Manager..."

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar si estamos en la carpeta correcta
if [ ! -f "manage.py" ]; then
    print_error "No se encuentra manage.py. Ejecuta este script en la carpeta del proyecto."
    exit 1
fi

# Actualizar sistema
print_message "Actualizando sistema..."
sudo apt update

# Instalar Python y herramientas necesarias
print_message "Instalando Python y dependencias..."
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    print_message "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
print_message "Activando entorno virtual..."
source venv/bin/activate

# Verificar pip
print_message "Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
print_message "Instalando dependencias Python..."
pip install -r requirements.txt

# Configurar base de datos
print_message "Configurando base de datos..."
python manage.py migrate

# Crear directorio media si no existe
print_message "Creando directorios necesarios..."
mkdir -p media/evidencias media/informes_cierre

# Poblar datos iniciales
print_message "Creando usuarios e integrantes..."
if python manage.py shell < seed_integrantes.py; then
    print_message "✓ Integrantes creados"
else
    print_warning "Error al crear integrantes, probablemente ya existen"
fi

print_message "Estableciendo contraseñas..."
if python manage.py shell < reset_passwords.py; then
    print_message "✓ Contraseñas configuradas"
else
    print_warning "Error al resetear contraseñas"
fi

print_message "Cargando tareas del sprint..."
if python manage.py shell < seed_backlog.py; then
    print_message "✓ Tareas cargadas"
else
    print_warning "Error al cargar tareas, probablemente ya existen"
fi

# Crear superusuario admin si no existe
print_message "Creando usuario administrador..."
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@neusi.com', 'admin123')
        print('✓ Usuario admin creado')
    else:
        print('✓ Usuario admin ya existe')
except Exception as e:
    print(f'Error: {e}')
EOF

# Configurar permisos
print_message "Configurando permisos de archivos..."
chmod 755 media/
chmod -R 755 media/evidencias/ media/informes_cierre/ 2>/dev/null || true

# Recolectar archivos estáticos (si los hubiera)
print_message "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput 2>/dev/null || true

print_message "¡Configuración completada!"
echo ""
echo "🎉 NEUSI Task Manager está listo para usar!"
echo ""
echo "📱 Para iniciar el servidor:"
echo "   cd $(pwd)"
echo "   source venv/bin/activate"
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
echo "🌐 Acceso:"
echo "   URL: http://$(hostname -I | awk '{print $1}'):8000"
echo "   URL local: http://localhost:8000"
echo ""
echo "🔑 Credenciales:"
echo "   Usuarios: daniel, andres_gomez (Administradores)"
echo "   Usuarios: laura, diana, samir, christiam, juan,"
echo "            diego_ortiz, andres_gonzalez, daniela, diego_gomez"
echo "   Contraseña: neusi123"
echo "   Admin Django: admin/admin123"
echo ""
echo "⚙️ Comandos útiles:"
echo "   Activar entorno: source venv/bin/activate"
echo "   Iniciar servidor: python manage.py runserver 0.0.0.0:8000"
echo "   Ver logs detallados: python manage.py runserver --verbosity=2"
echo "   Resetear datos: python manage.py flush && python manage.py shell < seed_backlog.py"
echo ""
print_message "Sistema listo para la exposición! 🎯"

# Mostrar IP del servidor para fácil acceso
SERVER_IP=$(hostname -I | awk '{print $1}')
print_message "Tu servidor estará disponible en: http://$SERVER_IP:8000"