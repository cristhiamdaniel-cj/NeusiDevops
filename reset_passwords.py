# reset_passwords.py
from django.contrib.auth.models import User

DEFAULT_PASSWORD = "neusi123"

for u in User.objects.all():
    u.set_password(DEFAULT_PASSWORD)  # 🔐 genera el hash correcto
    u.save()
    print(f"✅ Usuario {u.username} reseteado a {DEFAULT_PASSWORD}")

print("🎉 Contraseñas reseteadas.")
