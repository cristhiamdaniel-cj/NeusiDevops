# 🚀 NEUSI Task Manager

Sistema de gestión de tareas y disponibilidad para equipos de desarrollo, implementado con Django.

## 📋 Tabla de Contenidos

- [Características](#características)
- [Tecnologías](#tecnologías)
- [Instalación](#instalación)
- [Configuración de Desarrollo](#configuración-de-desarrollo)
- [Usuarios y Contraseñas](#usuarios-y-contraseñas)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Flujo de Trabajo Git](#flujo-de-trabajo-git)
- [Guía Rápida de Uso](#guía-rápida-de-uso)
- [Troubleshooting](#troubleshooting)
- [Backup y Restauración](#backup-y-restauración)
- [Equipo de Desarrollo](#equipo-de-desarrollo)

## ✨ Características

### Gestión de Tareas
- **Backlog en Lista** - Vista completa de todas las tareas con filtros por persona, sprint y estado
- **Matriz de Eisenhower** - Organización por urgencia e importancia (UI, NUI, UNI, NUNI)
- **Kanban Board** - Flujo de trabajo visual con drag & drop (Nuevo → Aprobado → En Progreso → Completado → Bloqueado)
- **Estados de Tarea** - Los usuarios pueden mover sus propias tareas entre estados
- **Evidencias** - Adjuntar archivos y comentarios a cada tarea
- **Permisos por Rol** - Control de acceso basado en roles

### Disponibilidad Horaria
- **Configuración Semanal** - Define tu disponibilidad hora por hora (7 días x 24 horas)
- **Vista de Equipo** - Consulta la disponibilidad de todos los miembros
- **Código de Colores** - Disponible (verde), Ocupado (rojo), Tentativo (amarillo)
- **Actualización Semanal** - Ventana de edición automatizada

### Daily Scrum
- **Registro Diario** - ¿Qué hiciste ayer? ¿Qué harás hoy? ¿Impedimentos?
- **Control de Horario** - Alertas si se registra fuera de 7-9 AM
- **Resumen de Dailies** - Vista de todos los dailies del equipo (últimos 7 días)

### Sistema de Sprints
- **Gestión de Sprints** - Crear y gestionar períodos de trabajo
- **Asignación por Sprint** - Organizar tareas en sprints específicos

## 🛠️ Tecnologías

- **Backend**: Django 5.2.6
- **Base de Datos**: SQLite (desarrollo)
- **Frontend**: Bootstrap 5.3, JavaScript vanilla
- **Autenticación**: Django Auth System
- **Gestión de Archivos**: Django File Storage

## 📦 Instalación

### Requisitos Previos
- Python 3.12+
- pip
- virtualenv
- Git

### Clonar el Repositorio

```bash
git clone https://github.com/cristhiamdaniel-cj/NeusiDevops.git
cd NeusiDevops/NeusiDevops
```

### Configurar Entorno Virtual

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate  # Linux/Mac
# O en Windows:
venv\Scripts\activate
```

### Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Configurar Base de Datos

```bash
# Ejecutar migraciones
python manage.py migrate

# IMPORTANTE: Cargar usuarios del equipo
python manage.py shell < seed_integrantes.py
```

### Iniciar Servidor

```bash
python manage.py runserver
```

Acceder a: `http://localhost:8000`

## 🔧 Configuración de Desarrollo

### Estructura de Ramas Git

```
main            # Rama principal de producción
  ├─ develop    # Rama de desarrollo compartida
  ├─ dev/daniel # Rama personal de Daniel (backend)
  └─ dev/juan   # Rama personal de Juan (frontend)
```

### Trabajar en tu Rama Personal

```bash
# Cambiar a tu rama
git checkout dev/daniel  # o dev/juan

# Hacer cambios y commits
git add .
git commit -m "feat: descripción del cambio"
git push origin dev/daniel

# Cuando tu feature esté lista, hacer merge a develop
git checkout develop
git pull origin develop
git merge dev/daniel
git push origin develop
```

### Convenciones de Commits

Usa estos prefijos para mantener el historial organizado:

- `feat:` - Nueva funcionalidad
- `fix:` - Corrección de bugs
- `refactor:` - Refactorización de código
- `docs:` - Cambios en documentación
- `style:` - Cambios de formato/UI
- `test:` - Agregar o modificar tests
- `chore:` - Tareas de mantenimiento

**Ejemplos:**
```bash
git commit -m "feat: Add task filtering by sprint in Kanban"
git commit -m "fix: Correct drag and drop URL in Kanban board"
git commit -m "style: Improve task card design in backlog"
```

## 👥 Usuarios y Contraseñas

### Formato de Contraseñas
Todos los usuarios usan el formato: `nombreusuario_123`

### Administradores (pueden crear/editar/eliminar tareas)

| Usuario | Contraseña | Nombre Completo | Rol |
|---------|------------|-----------------|-----|
| `daniel` | `daniel_123` | Daniel Campos | Líder BD |
| `andres_gomez` | `andres_gomez_123` | Andrés Gómez | Scrum Master/PO |

### Desarrolladores

| Usuario | Contraseña | Nombre Completo |
|---------|------------|-----------------|
| `juan` | `juan_123` | Juan Santa María |
| `andres_gonzalez` | `andres_gonzalez_123` | Andrés González |
| `christian` | `christian_123` | Christian Jiménez |
| `daniela` | `daniela_123` | Daniela Mazuera |
| `diana` | `diana_123` | Diana Marín |
| `diego_gomez` | `diego_gomez_123` | Diego Gómez |
| `diego_ortiz` | `diego_ortiz_123` | Diego Ortiz |
| `laura` | `laura_123` | Laura Rivera |
| `samir` | `samir_123` | Samir Sánchez |

### Cambiar Contraseña

Al iniciar sesión por primera vez, se recomienda cambiar tu contraseña:

1. Ir a tu perfil (arriba a la derecha)
2. Click en "Cambiar Contraseña"
3. Ingresar contraseña actual y nueva contraseña

O desde la terminal:

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User
user = User.objects.get(username='tu_usuario')
user.set_password('nueva_contraseña')
user.save()
exit()
```

## 🗂️ Estructura del Proyecto

```
NeusiDevops/
├── backlog/                    # App principal de gestión de tareas
│   ├── models.py              # Modelos: Tarea, Sprint, Integrante, Daily, Evidencia
│   ├── views.py               # Vistas y lógica de negocio
│   ├── forms.py               # Formularios Django
│   ├── urls.py                # Rutas de la aplicación
│   ├── templates/             # Templates HTML
│   │   ├── backlog_list.html
│   │   ├── kanban.html
│   │   ├── matriz.html
│   │   └── ...
│   └── migrations/            # Migraciones de base de datos
├── disponibilidad/            # App de gestión de horarios
│   ├── models.py              # DisponibilidadSemanal, HorarioDisponibilidad
│   ├── views.py               # Vistas de disponibilidad
│   ├── templates/             # Templates de disponibilidad
│   └── templatetags/          # Filtros personalizados
│       └── disponibilidad_filters.py
├── neusi_tasks/               # Configuración del proyecto
│   ├── settings.py            # Configuración Django
│   ├── urls.py                # URLs principales
│   └── wsgi.py                # WSGI config
├── templates/                 # Templates base
│   └── base.html             # Template principal
├── media/                     # Archivos subidos (evidencias, informes)
├── db.sqlite3                # Base de datos (NO en repo)
├── manage.py                 # Gestor Django
├── requirements.txt          # Dependencias Python
├── README.md                 # Este archivo
├── CONTRIBUTING.md           # Guía de contribución
└── .gitignore               # Archivos excluidos de Git
```

## 🔄 Flujo de Trabajo Git

### Para Daniel (Backend)

```bash
# 1. Asegurarte de estar en tu rama
git checkout dev/daniel

# 2. Obtener últimos cambios de develop
git pull origin develop

# 3. Trabajar en tu código
# ... hacer cambios ...

# 4. Guardar cambios
git add .
git commit -m "feat: add new backend feature"
git push origin dev/daniel

# 5. Cuando esté listo para integrar
git checkout develop
git pull origin develop
git merge dev/daniel
git push origin develop

# 6. Actualizar main (solo cuando sea estable)
git checkout main
git merge develop
git push origin main
```

### Para Juan (Frontend)

```bash
# 1. Clonar repositorio (primera vez)
git clone https://github.com/cristhiamdaniel-cj/NeusiDevops.git
cd NeusiDevops/NeusiDevops

# 2. Crear tu rama personal
git checkout -b dev/juan

# 3. Configurar entorno
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate

# 4. Trabajar en frontend
# ... hacer cambios en templates, CSS, JS ...

# 5. Guardar cambios
git add .
git commit -m "style: improve UI design"
git push origin dev/juan

# 6. Integrar a develop cuando esté listo
git checkout develop
git pull origin develop
git merge dev/juan
git push origin develop
```

### Resolver Conflictos

Si hay conflictos al hacer merge:

```bash
# Git te mostrará los archivos en conflicto
git status

# Editar archivos manualmente para resolver conflictos
# Buscar marcadores: <<<<<<< , ======= , >>>>>>>

# Después de resolver
git add archivo_resuelto.py
git commit -m "merge: resolve conflicts from dev/juan"
git push origin develop
```

## 🚀 Guía Rápida de Uso

### Crear una Tarea (Solo Administradores)

1. Ir a "Backlog" → "Nueva tarea"
2. Completar:
   - **Título**: Nombre descriptivo de la tarea
   - **Descripción**: Detalles completos
   - **Categoría**: UI, NUI, UNI, NUNI
   - **Sprint**: Sprint asignado
   - **Asignado a**: Desarrollador responsable
   - **Criterios de Aceptación** (opcional)
3. Guardar

### Mover Tareas en Kanban (Todos los usuarios)

1. Ir a "Ver Kanban"
2. Arrastrar tu tarjeta a la columna deseada:
   - **Nuevo**: Tarea recién creada
   - **Aprobado**: Tarea revisada y lista para trabajar
   - **En Progreso**: Trabajando activamente
   - **Completado**: Tarea terminada
   - **Bloqueado**: Hay impedimentos
3. El estado se actualiza automáticamente

### Registrar Daily

1. Ir a "Mi Daily de Hoy"
2. Completar:
   - **¿Qué hice ayer?**: Resumen del día anterior
   - **¿Qué haré hoy?**: Plan para hoy
   - **¿Impedimentos?**: Obstáculos encontrados
3. Guardar (preferiblemente entre 7-9 AM)

### Configurar Disponibilidad

1. Ir a "Mi Horario Semanal"
2. Hacer clic en cada casilla para cambiar estado:
   - **Verde** = Disponible
   - **Rojo** = Ocupado
   - **Amarillo** = Tentativo
3. Los cambios se guardan automáticamente
4. Puedes editar tu horario cada semana

### Agregar Evidencia a una Tarea

1. Abrir la tarea desde el Backlog
2. Ir a la sección "Evidencias"
3. Click en "Agregar Evidencia"
4. Adjuntar archivo y/o escribir comentario
5. Guardar

### Cerrar Tarea

1. Ir a la tarea en el Backlog
2. Click en "Cerrar Tarea"
3. **Obligatorio**: Adjuntar informe de cierre
4. Confirmar cierre
5. La tarea se marcará como cerrada y no podrá editarse

## 🐛 Troubleshooting

### Error: "No such table"

```bash
python manage.py migrate
```

### Error: "No module named..."

```bash
pip install -r requirements.txt
```

### Base de Datos Corrupta

```bash
# CUIDADO: Esto borra todos los datos
rm db.sqlite3
python manage.py migrate
python manage.py shell < seed_integrantes.py
```

### Puerto 8000 Ya Está en Uso

```bash
# Ver qué proceso usa el puerto
sudo lsof -i :8000
# O
sudo netstat -tulpn | grep 8000

# Matar proceso
kill -9 <PID>

# Iniciar servidor en otro puerto
python manage.py runserver 8080
```

### Servicio Systemd No Funciona

```bash
# Ver estado
sudo systemctl status neusi-backend.service

# Ver logs
sudo journalctl -u neusi-backend.service -n 50 --no-pager

# Reiniciar servicio
sudo systemctl restart neusi-backend.service

# Verificar que el venv existe
ls -la /home/desarrollo/NeuralWasi/NeusiDevops/NeusiDevops/venv/bin/python
```

### Problemas con Archivos Estáticos

```bash
python manage.py collectstatic
```

### Error de Permisos en Media/

```bash
# Dar permisos correctos
sudo chown -R $USER:$USER media/
chmod -R 755 media/
```

### Venv Corrupto

```bash
# Eliminar venv
rm -rf venv

# Recrear
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 📝 Backup y Restauración

### Crear Backup Manual

```bash
# Crear directorio de backups si no existe
mkdir -p backups

# Backup de base de datos
DATE=$(date +%Y%m%d_%H%M%S)
cp db.sqlite3 backups/db.sqlite3.backup_$DATE

# Backup de archivos subidos
tar -czf backups/media_$DATE.tar.gz media/

echo "Backup creado: $DATE"
```

### Script de Backup Automático

```bash
cat > backup_db.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p backups
cp db.sqlite3 backups/db.sqlite3.backup_$DATE
tar -czf backups/media_$DATE.tar.gz media/
echo "Backup creado: db.sqlite3.backup_$DATE"
EOF

chmod +x backup_db.sh

# Ejecutar antes de cambios importantes
./backup_db.sh
```

### Restaurar desde Backup

```bash
# Listar backups disponibles
ls -lh backups/

# Restaurar base de datos
cp backups/db.sqlite3.backup_YYYYMMDD_HHMMSS db.sqlite3

# Restaurar archivos
tar -xzf backups/media_YYYYMMDD_HHMMSS.tar.gz

# Reiniciar servicio
sudo systemctl restart neusi-backend.service
```

### Backup Automático con Cron

```bash
# Editar crontab
crontab -e

# Agregar línea para backup diario a las 2 AM
0 2 * * * cd /home/desarrollo/NeuralWasi/NeusiDevops/NeusiDevops && ./backup_db.sh
```

## 🔒 Seguridad

### Mejores Prácticas

1. **Cambiar contraseñas** después del primer login
2. **No compartir** credenciales de administrador
3. **Hacer backup** antes de cambios importantes
4. **Revisar logs** regularmente
5. **Mantener** Django y dependencias actualizadas

### Actualizar Dependencias

```bash
# Ver paquetes desactualizados
pip list --outdated

# Actualizar un paquete específico
pip install --upgrade django

# Actualizar requirements.txt
pip freeze > requirements.txt
```

## 📚 Recursos Adicionales

### Documentación Oficial
- [Django Documentation](https://docs.djangoproject.com/)
- [Bootstrap 5 Docs](https://getbootstrap.com/docs/5.3/)
- [Git Documentation](https://git-scm.com/doc)

### Tutoriales Recomendados
- [Django Girls Tutorial](https://tutorial.djangogirls.org/)
- [MDN Django Tutorial](https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django)
- [Real Python - Django Tutorials](https://realpython.com/tutorials/django/)

### Herramientas Útiles
- [Django Debug Toolbar](https://django-debug-toolbar.readthedocs.io/)
- [DB Browser for SQLite](https://sqlitebrowser.org/)
- [Postman](https://www.postman.com/) (para testing de APIs)

## 👨‍💻 Equipo de Desarrollo

| Nombre | Rol | Responsabilidades |
|--------|-----|-------------------|
| **Daniel Campos** | Backend Lead | Arquitectura, DevOps, Base de datos |
| **Juan** | Frontend Developer | UI/UX, Diseño, Templates |
| **Andrés Gómez** | Scrum Master / PO | Gestión, Priorización, Testing |

## 🆘 Soporte

Para problemas o preguntas:

1. **Revisar esta documentación** y CONTRIBUTING.md
2. **Buscar en issues** del repositorio GitHub
3. **Crear un issue** si es un bug nuevo
4. **Contactar** a Daniel Campos o Andrés Gómez

### Reportar un Bug

Al reportar un bug, incluir:
- Descripción del problema
- Pasos para reproducirlo
- Comportamiento esperado vs actual
- Capturas de pantalla (si aplica)
- Logs de error

## 📄 Licencia

Este proyecto es privado y de uso interno del equipo NEUSI.

---

**Última actualización**: Septiembre 30, 2025  
**Versión**: 1.0.0  
**Estado**: Producción  
**URL Producción**: https://devops-neusi.ngrok.io
