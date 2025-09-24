from django.contrib.auth.models import User
from backlog.models import Integrante

# 🔑 Contraseña por defecto para todos los integrantes
PASSWORD_DEFAULT = "neusi123"

for integrante in Integrante.objects.all():
    username = integrante.user.username if integrante.user else None

    # Si ya tiene usuario vinculado, lo saltamos
    if integrante.user:
        print(f"✅ {integrante.user.username} ya tiene cuenta, saltando...")
        continue

    # Usamos el primer nombre en minúsculas + apellido si está disponible
    base_username = (
        integrante.user.first_name.lower().split()[0]
        if integrante.user else integrante.nombre.split()[0].lower()
    )
    username = base_username

    # Evitar duplicados
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    # Creamos el usuario
    user = User.objects.create_user(
        username=username,
        first_name=integrante.user.first_name if integrante.user else integrante.nombre,
        password=PASSWORD_DEFAULT
    )

    # Vinculamos el usuario al integrante
    integrante.user = user
    integrante.save()

    print(f"👤 Usuario creado: {username} → Integrante {integrante}")

print("🎉 Migración completada: todos los integrantes tienen login.")
