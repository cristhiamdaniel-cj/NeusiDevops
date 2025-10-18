#!/bin/bash
# ==========================================================
# Script: informe_codigo_neusitaskmanager.sh
# Objetivo: Generar informe técnico del código actual de NEUSI Task Manager
# Autor: Daniel Campos – NEUSI Solutions
# ==========================================================

BASE_DIR="/home/desarrollo/NeuralWasi/NeusiDevops"
OUTPUT_FILE="${BASE_DIR}/informe_codigo_neusitaskmanager.txt"

# 🔍 Buscar automáticamente el manage.py
PROJECT_DIR=$(find "$BASE_DIR" -maxdepth 3 -name "manage.py" -exec dirname {} \; | head -n 1)

if [ -z "$PROJECT_DIR" ]; then
  echo "❌ No se encontró manage.py en ${BASE_DIR}. Revisa la ruta del proyecto."
  exit 1
fi

echo "📊 Generando informe técnico del proyecto NEUSI Task Manager..."
echo "==============================================================" > "$OUTPUT_FILE"
echo "📅 Fecha: $(date)" >> "$OUTPUT_FILE"
echo "📂 Proyecto detectado: $PROJECT_DIR" >> "$OUTPUT_FILE"
echo "==============================================================" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 1️⃣ Estructura de directorios
echo "📁 ESTRUCTURA DE DIRECTORIOS:" >> "$OUTPUT_FILE"
tree -L 3 "$PROJECT_DIR" >> "$OUTPUT_FILE" 2>/dev/null
echo "" >> "$OUTPUT_FILE"

# 2️⃣ Estadísticas de código
echo "📏 ESTADÍSTICAS DE CÓDIGO:" >> "$OUTPUT_FILE"
find "$PROJECT_DIR" -name "*.py" | wc -l | awk '{print "Archivos Python:", $1}' >> "$OUTPUT_FILE"
find "$PROJECT_DIR" -name "*.html" | wc -l | awk '{print "Plantillas HTML:", $1}' >> "$OUTPUT_FILE"
find "$PROJECT_DIR" -name "*.js" | wc -l | awk '{print "Archivos JS:", $1}' >> "$OUTPUT_FILE"
find "$PROJECT_DIR" -name "*.py" -exec cat {} + | wc -l | awk '{print "Líneas totales Python:", $1}' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 3️⃣ Aplicaciones Django
echo "🧩 APLICACIONES DETECTADAS:" >> "$OUTPUT_FILE"
grep -r "class " "$PROJECT_DIR" | grep "AppConfig" | awk -F ":" '{print $1}' | sort -u >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 4️⃣ Modelos
echo "🗄️ MODELOS DETECTADOS:" >> "$OUTPUT_FILE"
grep -r "class " "$PROJECT_DIR" | grep "(models.Model)" | awk -F ":" '{print $1}' | sort -u >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 5️⃣ Vistas
echo "👁️‍🗨️ VISTAS DEFINIDAS:" >> "$OUTPUT_FILE"
grep -r "def " "$PROJECT_DIR" | grep "request" | head -n 25 >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 6️⃣ Endpoints
echo "🌐 ENDPOINTS / URLs:" >> "$OUTPUT_FILE"
grep -r "path(" "$PROJECT_DIR" | awk -F ":" '{print $2}' >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# 7️⃣ Dependencias
echo "📦 DEPENDENCIAS (requirements.txt):" >> "$OUTPUT_FILE"
if [ -f "$BASE_DIR/requirements.txt" ]; then
  cat "$BASE_DIR/requirements.txt" >> "$OUTPUT_FILE"
else
  echo "No se encontró requirements.txt" >> "$OUTPUT_FILE"
fi
echo "" >> "$OUTPUT_FILE"

echo "✅ Informe generado en: $OUTPUT_FILE"

