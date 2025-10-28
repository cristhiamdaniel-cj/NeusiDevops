#!/bin/bash

PROJECT_DIR="/home/desarrollo/NeuralWasi/NeusiDevops"
DB_PATH="$PROJECT_DIR/db.sqlite3"
MEDIA_DIR="$PROJECT_DIR/media"

echo "=========================================="
echo "  🔗 Vinculación de Evidencias Huérfanas"
echo "=========================================="
echo ""

# Crear respaldo de la BD
echo "📦 Creando respaldo de la base de datos..."
cp "$DB_PATH" "${DB_PATH}.backup_$(date +%Y%m%d_%H%M%S)"
echo "✅ Respaldo creado"
echo ""

# Mapeo manual de archivos conocidos a tareas
declare -A ARCHIVO_TAREA=(
    ["Configurar_entorno_PostgreSQL_y_archivo.pdf"]="165"
    ["Implementar_Roles_de_Usuario.pdf"]="167"
    ["Implementar_respaldo_y_restauración_PostgreSQL.pdf"]="168"
    ["Ajustes_Varios_de_desarrollo.pdf"]="211"
    ["Auditoría_de_identidad_visual_actual_de_NEUSI.pdf"]="151"
    ["BrandKit_NEUSI.png"]="155"
    ["Leads_Gestion_Completa_NEUSI.xlsx"]="161"
    ["LOGOS_CON_TIPOGRAFÍA_INSTITUCIONAL_MODIFICADA.zip"]="153"
)

echo "🔗 Vinculando archivos a tareas..."
echo ""

for archivo in "${!ARCHIVO_TAREA[@]}"; do
    tarea_id="${ARCHIVO_TAREA[$archivo]}"
    ruta_completa="evidencias/$archivo"
    
    # Verificar si el archivo existe
    if [ -f "$MEDIA_DIR/$ruta_completa" ]; then
        # Verificar si ya existe una evidencia para esta tarea
        existe=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_evidencia WHERE tarea_id = $tarea_id AND archivo = '$ruta_completa';")
        
        if [ "$existe" -eq 0 ]; then
            # Obtener info de la tarea
            tarea_info=$(sqlite3 "$DB_PATH" "SELECT titulo, asignado_a_id FROM backlog_tarea WHERE id = $tarea_id;")
            titulo=$(echo "$tarea_info" | cut -d'|' -f1)
            asignado_id=$(echo "$tarea_info" | cut -d'|' -f2)
            
            # Obtener user_id del integrante
            if [ -n "$asignado_id" ]; then
                user_id=$(sqlite3 "$DB_PATH" "SELECT user_id FROM backlog_integrante WHERE id = $asignado_id;")
            else
                user_id=""
            fi
            
            # Insertar evidencia
            fecha_actual=$(date '+%Y-%m-%d %H:%M:%S')
            
            sqlite3 "$DB_PATH" <<SQL
INSERT INTO backlog_evidencia (archivo, tarea_id, creado_en, actualizado_en, creado_por_id, comentario)
VALUES ('$ruta_completa', $tarea_id, '$fecha_actual', '$fecha_actual', $user_id, 'Evidencia vinculada automáticamente desde archivo huérfano');
SQL
            
            if [ $? -eq 0 ]; then
                echo "  ✅ Tarea $tarea_id: $archivo → Vinculado"
            else
                echo "  ❌ Tarea $tarea_id: Error al vincular"
            fi
        else
            echo "  ⏭️  Tarea $tarea_id: Ya existe evidencia"
        fi
    else
        echo "  ⚠️  Archivo no encontrado: $archivo"
    fi
done

echo ""
echo "=========================================="
echo "📊 RESUMEN POST-VINCULACIÓN:"
echo "=========================================="

sqlite3 -header -column "$DB_PATH" <<EOF
.mode column
.headers on

SELECT 'Evidencias en BD' as 'Métrica', COUNT(*) as 'Cantidad'
FROM backlog_evidencia
UNION ALL
SELECT 'Con archivo adjunto', COUNT(*)
FROM backlog_evidencia
WHERE archivo IS NOT NULL AND archivo != '';
EOF

echo ""
echo "📋 Evidencias del Sprint 1:"
sqlite3 -header -column "$DB_PATH" <<EOF
SELECT 
    e.id,
    t.id as 'Tarea',
    SUBSTR(t.titulo, 1, 40) as 'Título',
    t.estado,
    SUBSTR(e.archivo, 12, 30) as 'Archivo'
FROM backlog_evidencia e
INNER JOIN backlog_tarea t ON e.tarea_id = t.id
WHERE t.sprint_id = 1
ORDER BY e.id;
EOF

echo ""
echo "=========================================="
echo "✅ Vinculación completada"
echo "=========================================="
echo ""
echo "💡 Ahora ejecuta nuevamente:"
echo "   ./scripts/sprint_stats.sh"
echo ""
