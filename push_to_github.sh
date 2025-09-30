#!/bin/bash
# push_to_github.sh - Subir proyecto NEUSI al repositorio

echo "📤 Subiendo NEUSI Task Manager a GitHub..."

# Verificar si estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ No se encuentra manage.py. Ejecuta este script en la carpeta app-neusi"
    exit 1
fi

# Inicializar git si no está inicializado
if [ ! -d ".git" ]; then
    echo "🔧 Inicializando repositorio Git..."
    git init
fi

# Agregar archivos al repositorio
echo "📁 Agregando archivos..."

# Crear .gitignore si no existe
if [ ! -f ".gitignore" ]; then
    echo "📝 Creando .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Virtual Environment
venv
venv/
env/
ENV/

# Media files
media/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Static files collected
staticfiles/
static_collected/
EOF
fi

# Crear requirements.txt si no existe
if [ ! -f "requirements.txt" ]; then
    echo "📝 Creando requirements.txt..."
    cat > requirements.txt << 'EOF'
Django==5.2.6
Pillow==10.0.1
EOF
fi

# Agregar todos los archivos
git add .

# Hacer commit
echo "💾 Realizando commit..."
git commit -m "Initial commit: NEUSI Task Manager

- Sistema de gestión de tareas con Matriz de Eisenhower
- Control de permisos por roles (Daniel/Andrés vs equipo)
- Sistema de Daily Scrum (7-8 AM)
- Gestión de evidencias y archivos
- Proceso controlado de cierre de tareas
- 36 tareas del sprint 22-29 septiembre
- 11 integrantes del equipo NEUSI"

# Configurar rama principal
git branch -M main

# Agregar remoto (tu repositorio)
REPO_URL="https://github.com/cristhiamdaniel-cj/NeusiDevops.git"
echo "🔗 Configurando repositorio remoto: $REPO_URL"

# Remover remote existente si existe
git remote remove origin 2>/dev/null || true
git remote add origin $REPO_URL

# Subir al repositorio
echo "🚀 Subiendo archivos a GitHub..."
git push -u origin main

echo "✅ ¡Proyecto subido exitosamente!"
echo ""
echo "📍 Tu repositorio está en:"
echo "   $REPO_URL"
echo ""
echo "🖥️  Para clonar en el servidor:"
echo "   git clone $REPO_URL"
echo "   cd NeusiDevops"
echo "   chmod +x setup_server.sh"
echo "   ./setup_server.sh"
echo ""
echo "🎯 ¡Listo para la exposición!"