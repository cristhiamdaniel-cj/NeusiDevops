#!/bin/bash
# edit_urls.sh
# Conecta backlog/urls.py al proyecto principal

cat > neusi_tasks/urls.py << 'EOF'
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('backlog.urls')),
]
EOF

echo "✅ URLs globales configuradas."

