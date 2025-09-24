# sync_integrantes_users.py
from django.contrib.auth.models import User
from backlog.models import Integrante

def run():
    for integrante in Integrante.objects.all():
        try:
            user = User.objects.get(username=integrante.user.username)
            if integrante.user != user:
                integrante.user = user
                integrante.save()
                print(f"🔗 Vinculado {integrante} -> {user.username}")
        except Exception as e:
            print(f"⚠️ No se pudo vincular {integrante}: {e}")
