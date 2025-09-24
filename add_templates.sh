#!/bin/bash
# add_templates.sh
# Crea las plantillas básicas backlog.html y checklist.html

mkdir -p backlog/templates/backlog

cat > backlog/templates/backlog/backlog.html << 'EOF'
{% extends "base.html" %}

{% block content %}
<h2>📋 Backlog de NEUSI</h2>
<div>
    {% for tarea in tareas %}
        <div style="border:1px solid #ccc; margin:5px; padding:10px;">
            <h4>{{ tarea.titulo }}</h4>
            <p><b>Categoría:</b> {{ tarea.get_categoria_display }}</p>
            <p><b>Asignado:</b> {{ tarea.asignado_a }}</p>
            <p><b>Estado:</b> {% if tarea.completada %} ✅ Cerrada {% else %} ⏳ Abierta {% endif %}</p>
            <a href="{% url 'cerrar_tarea' tarea.id %}">Cerrar tarea</a>
        </div>
    {% empty %}
        <p>No hay tareas en el backlog.</p>
    {% endfor %}
</div>
{% endblock %}
EOF

cat > backlog/templates/backlog/checklist.html << 'EOF'
{% extends "base.html" %}

{% block content %}
<h2>✅ Checklist de {{ integrante }}</h2>
<ul>
    {% for tarea in tareas %}
        <li>{{ tarea.titulo }} ({{ tarea.get_categoria_display }})</li>
    {% empty %}
        <li>No tienes tareas asignadas en este sprint.</li>
    {% endfor %}
</ul>
<a href="{% url 'backlog' %}">⬅ Volver al backlog</a>
{% endblock %}
EOF

# Crear base.html simple
mkdir -p templates
cat > templates/base.html << 'EOF'
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>NEUSI Tasks</title>
</head>
<body>
    <header>
        <h1>🚀 NEUSI Task Manager</h1>
        <hr>
    </header>
    <main>
        {% block content %}{% endblock %}
    </main>
</body>
</html>
EOF

echo "✅ Plantillas creadas en backlog/templates/backlog/"

