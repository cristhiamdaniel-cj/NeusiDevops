#!/bin/bash

PROJECT_DIR="/home/desarrollo/NeuralWasi/NeusiDevops"
DB_PATH="$PROJECT_DIR/db.sqlite3"
MEDIA_DIR="$PROJECT_DIR/media"

echo "=========================================="
echo "  🔍 Análisis de Archivos Huérfanos"
echo "=========================================="
echo ""

# 1. Archivos en media/evidencias
echo "📁 Archivos en media/evidencias/:"
ls -1 "$MEDIA_DIR/evidencias/" 2>/dev/null | while read archivo; do
    # Buscar en BD
    EN_BD=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_evidencia WHERE archivo LIKE '%$archivo%';")
    if [ "$EN_BD" -eq 0 ]; then
        echo "  ❌ HUÉRFANO: $archivo"
        
        # Intentar adivinar la tarea por el nombre
        TAREA_MATCH=$(echo "$archivo" | sed 's/_/ /g' | sed 's/\.pdf//g' | sed 's/\.png//g' | sed 's/\.xlsx//g' | sed 's/\.docx//g' | sed 's/\.zip//g')
        echo "     Posible tarea: $TAREA_MATCH"
    else
        echo "  ✅ VINCULADO: $archivo"
    fi
done
echo ""

# 2. Archivos en media/informes_cierre
echo "📁 Archivos en media/informes_cierre/:"
ls -1 "$MEDIA_DIR/informes_cierre/" 2>/dev/null | while read archivo; do
    EN_BD=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE informe_cierre LIKE '%$archivo%';")
    if [ "$EN_BD" -eq 0 ]; then
        echo "  ❌ HUÉRFANO: $archivo"
    else
        echo "  ✅ VINCULADO: $archivo"
    fi
done
echo ""

# 3. Resumen
TOTAL_EVIDENCIAS=$(ls -1 "$MEDIA_DIR/evidencias/" 2>/dev/null | wc -l)
TOTAL_INFORMES=$(ls -1 "$MEDIA_DIR/informes_cierre/" 2>/dev/null | wc -l)
REGISTROS_BD=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_evidencia WHERE archivo IS NOT NULL AND archivo != '';")

echo "=========================================="
echo "📊 RESUMEN:"
echo "   - Archivos en evidencias/: $TOTAL_EVIDENCIAS"
echo "   - Archivos en informes_cierre/: $TOTAL_INFORMES"
echo "   - Total archivos físicos: $(($TOTAL_EVIDENCIAS + $TOTAL_INFORMES))"
echo "   - Registros en BD con archivo: $REGISTROS_BD"
echo "   - Archivos huérfanos: $(($TOTAL_EVIDENCIAS + $TOTAL_INFORMES - $REGISTROS_BD))"
echo "=========================================="
echo ""

# 4. Sugerencias por archivo
echo "💡 SUGERENCIAS DE VINCULACIÓN:"
echo ""
echo "Basado en nombres de archivo, estas podrían ser las tareas:"
echo ""

sqlite3 -header -column "$DB_PATH" <<EOF
SELECT 
    t.id,
    t.titulo,
    t.estado,
    t.sprint_id
FROM backlog_tarea t
WHERE t.sprint_id = 1
  AND (
    t.titulo LIKE '%PostgreSQL%'
    OR t.titulo LIKE '%Roles%'
    OR t.titulo LIKE '%respaldo%'
    OR t.titulo LIKE '%BrandKit%'
    OR t.titulo LIKE '%identidad visual%'
    OR t.titulo LIKE '%logo%'
    OR t.titulo LIKE '%balance%'
    OR t.titulo LIKE '%Siigo%'
    OR t.titulo LIKE '%leads%'
  )
ORDER BY t.id;
EOF

echo ""
echo "=========================================="
