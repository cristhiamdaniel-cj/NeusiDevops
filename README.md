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

