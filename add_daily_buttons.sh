#!/bin/bash
# Script para añadir botones de Backlog y Daily en base.html
# y actualizar daily_resumen.html con links a los formularios.

set -e

echo "🔧 Añadiendo botones en base.html..."
cat > backlog/templates/base.html << 'EOF'
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>NEUSI Task Manager</title>
</head>
<body>
    <header style="background:#f5f5f5; padding:10px; margin-bottom:20px; border-bottom:2px solid #ccc;">
        <h1>🚀 NEUSI Task Manager</h1>
        <nav>
            <a href="{% url 'backlog_lista' %}" style="margin-right:15px;">📋 Backlog</a>
            <a href="{% url 'daily_resumen' %}">📝 Daily</a>
        </nav>
    </header>

    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
EOF

echo "✅ base.html actualizado con botones Backlog y Daily."

echo "🔧 Actualizando daily_resumen.html..."
cat > backlog/templates/backlog/daily_resumen.html << 'EOF'
{% extends "base.html" %}
{% block content %}
<h2>�� Resumen de Dailies</h2>

<!-- Accesos rápidos a los daily de cada integrante -->
<p>
    {% for i in integrantes %}
        <a href="{% url 'daily_view' i.id %}" style="margin-right:10px;">
            ✍️ Daily de {{ i.user.first_name }}
        </a>
    {% endfor %}
</p>

<table border="1" cellpadding="5">
    <tr>
        <th>👤 Integrante</th>
        <th>📅 Fecha</th>
        <th>✅ Ayer</th>
        <th>🎯 Hoy</th>
        <th>⛔ Impedimentos</th>
    </tr>
    {% for d in registros %}
    <tr>
        <td>{{ d.integrante.user.first_name }}</td>
        <td>{{ d.fecha }}</td>
        <td>{{ d.que_hizo_ayer }}</td>
        <td>{{ d.que_hara_hoy }}</td>
        <td>{{ d.impedimentos|default:"-" }}</td>
    </tr>
    {% empty %}
    <tr><td colspan="5">No hay registros de daily.</td></tr>
    {% endfor %}
</table>
{% endblock %}
EOF

echo "✅ daily_resumen.html actualizado con links a los formularios de cada integrante."

