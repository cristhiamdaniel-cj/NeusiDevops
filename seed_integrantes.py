from django.contrib.auth.models import User
from backlog.models import Integrante

# --- 1. Limpiar datos viejos ---
print("🗑️ Eliminando Integrantes y Usuarios antiguos...")
Integrante.objects.all().delete()
User.objects.exclude(is_superuser=True).delete()  # Mantiene solo el admin

# --- 2. Lista final de integrantes únicos con roles específicos ---
usuarios = [
    ("laura", "Laura Rivera", "Contabilidad"),
    ("diana", "Diana Marin", "Administración"),
    ("daniel", "Daniel Campos", "Lider Bases de datos"),  # ✅ PUEDE CREAR TAREAS
    ("samir", "Samir Sanchez", "Apoyo B.D. y Backend"),
    ("christiam", "Christiam Jimenez", "Front Web"),
    ("juan", "Juan Santa Maria", "Asistente Front"),
    ("diego_ortiz", "Diego Ortiz", "Power BI"),
    ("andres_gonzalez", "Andrés Gonzalez", "Power BI"),
    ("daniela", "Daniela Mazuera", "Asistente BI"),
    ("andres_gomez", "Andrés Gomez", "Scrum Master / PO"),  # ✅ PUEDE CREAR TAREAS
    ("diego_gomez", "Diego Gomez", "3D"),
]

# --- 3. Insertar usuarios e integrantes ---
for username, nombre, rol in usuarios:
    user = User.objects.create(username=username, first_name=nombre)
    integrante = Integrante.objects.create(user=user, rol=rol)
    
    # Mostrar permisos especiales
    if integrante.puede_crear_tareas():
        print(f"✔ Integrante {integrante} creado ⭐ CON PERMISOS ESPECIALES (puede crear tareas y evidencias)")
    else:
        print(f"✔ Integrante {integrante} creado (sin permisos especiales)")

print("\n🎉 Reset completado con éxito.")
print("\n📋 RESUMEN DE PERMISOS:")
print("➕ Pueden crear tareas y agregar evidencias:")
print("   • Daniel Campos (Lider Bases de datos)")
print("   • Andrés Gomez (Scrum Master / PO)")
print("\n👀 Solo pueden ver tareas y cerrar las propias:")
print("   • Resto del equipo")