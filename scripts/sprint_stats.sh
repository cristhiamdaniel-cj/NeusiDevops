#!/bin/bash

##############################################
# Script de Estadísticas Semanales de Sprint
# Autor: NEUSI DevOps Team
# Descripción: Genera reportes automáticos del sprint actual
##############################################

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
PROJECT_DIR="/home/desarrollo/NeuralWasi/NeusiDevops"
DB_PATH="$PROJECT_DIR/db.sqlite3"
REPORTS_DIR="$PROJECT_DIR/reportes_sprint"
DATE=$(date +%Y-%m-%d)
DATETIME=$(date +"%Y-%m-%d %H:%M:%S")
WEEK=$(date +%Y-W%U)

# Crear directorio de reportes si no existe
mkdir -p "$REPORTS_DIR"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  📊 Reporte Semanal Sprint - $DATE${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Función para obtener el sprint actual basado en la fecha
get_current_sprint() {
    sqlite3 "$DB_PATH" <<EOF
SELECT id, nombre, inicio, fin 
FROM backlog_sprint 
WHERE DATE('now') BETWEEN inicio AND fin
LIMIT 1;
EOF
}

# Obtener sprint actual
SPRINT_INFO=$(get_current_sprint)

if [ -z "$SPRINT_INFO" ]; then
    echo -e "${YELLOW}⚠️  No hay un sprint activo para la fecha actual${NC}"
    # Obtener el próximo sprint
    SPRINT_INFO=$(sqlite3 "$DB_PATH" "SELECT id, nombre, inicio, fin FROM backlog_sprint WHERE inicio > DATE('now') ORDER BY inicio LIMIT 1;")
    if [ -z "$SPRINT_INFO" ]; then
        echo -e "${RED}❌ No se encontró ningún sprint${NC}"
        exit 1
    fi
    echo -e "${YELLOW}📅 Usando el próximo sprint disponible${NC}"
fi

SPRINT_ID=$(echo "$SPRINT_INFO" | cut -d'|' -f1)
SPRINT_NAME=$(echo "$SPRINT_INFO" | cut -d'|' -f2)
SPRINT_START=$(echo "$SPRINT_INFO" | cut -d'|' -f3)
SPRINT_END=$(echo "$SPRINT_INFO" | cut -d'|' -f4)

echo -e "${GREEN}✓ Sprint Actual: $SPRINT_NAME (ID: $SPRINT_ID)${NC}"
echo -e "  📅 Período: $SPRINT_START → $SPRINT_END"
echo ""

# Nombre del archivo de reporte
REPORT_FILE="$REPORTS_DIR/sprint_${SPRINT_ID}_${DATE}.txt"
CSV_FILE="$REPORTS_DIR/sprint_${SPRINT_ID}_${DATE}.csv"
HTML_FILE="$REPORTS_DIR/sprint_${SPRINT_ID}_${DATE}.html"

# Iniciar reporte
cat > "$REPORT_FILE" <<EOF
===============================================
   REPORTE SEMANAL - $SPRINT_NAME
===============================================
Generado: $DATETIME
Período Sprint: $SPRINT_START → $SPRINT_END
===============================================

EOF

# 1. RESUMEN GENERAL
echo -e "${BLUE}📊 Generando resumen general...${NC}"
sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

-- RESUMEN POR ESTADO
SELECT '=== RESUMEN POR ESTADO ===' as '';
SELECT 
    estado as 'Estado',
    COUNT(*) as 'Cantidad',
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_ID), 1) || '%' as 'Porcentaje',
    COALESCE(SUM(esfuerzo_sp), 0) as 'Story Points'
FROM backlog_tarea
WHERE sprint_id = $SPRINT_ID
GROUP BY estado
ORDER BY COUNT(*) DESC;

SELECT '' as '';
EOF

# 2. TAREAS POR INTEGRANTE
echo -e "${BLUE}👥 Generando estadísticas por integrante...${NC}"
sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT '=== PROGRESO POR INTEGRANTE ===' as '';
SELECT 
    COALESCE(u.username, 'SIN ASIGNAR') as 'Usuario',
    i.rol as 'Rol',
    COUNT(t.id) as 'Total',
    SUM(CASE WHEN t.estado = 'APROBADO' THEN 1 ELSE 0 END) as 'Aprobadas',
    SUM(CASE WHEN t.estado = 'EN_PROGRESO' THEN 1 ELSE 0 END) as 'En Progreso',
    SUM(CASE WHEN t.estado = 'NUEVO' THEN 1 ELSE 0 END) as 'Sin Iniciar',
    COALESCE(SUM(t.esfuerzo_sp), 0) as 'SP Total',
    SUM(CASE WHEN t.estado = 'APROBADO' THEN COALESCE(t.esfuerzo_sp, 0) ELSE 0 END) as 'SP Completo'
FROM backlog_tarea t
LEFT JOIN backlog_integrante i ON t.asignado_a_id = i.id
LEFT JOIN auth_user u ON i.user_id = u.id
WHERE t.sprint_id = $SPRINT_ID
GROUP BY u.username, i.rol
ORDER BY COUNT(t.id) DESC;

SELECT '' as '';
EOF

# 3. EVIDENCIAS
echo -e "${BLUE}📎 Analizando evidencias...${NC}"
sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT '=== ESTADO DE EVIDENCIAS ===' as '';
SELECT 
    'Tareas con evidencia' as 'Métrica',
    COUNT(DISTINCT e.tarea_id) as 'Cantidad'
FROM backlog_evidencia e
INNER JOIN backlog_tarea t ON e.tarea_id = t.id
WHERE t.sprint_id = $SPRINT_ID
UNION ALL
SELECT 
    'Tareas sin evidencia',
    COUNT(*)
FROM backlog_tarea t
LEFT JOIN backlog_evidencia e ON t.id = e.tarea_id
WHERE t.sprint_id = $SPRINT_ID AND e.id IS NULL
UNION ALL
SELECT 
    'Total evidencias subidas',
    COUNT(*)
FROM backlog_evidencia e
INNER JOIN backlog_tarea t ON e.tarea_id = t.id
WHERE t.sprint_id = $SPRINT_ID;

SELECT '' as '';

SELECT '=== ÚLTIMAS EVIDENCIAS SUBIDAS ===' as '';
SELECT 
    e.id as 'ID',
    t.id as 'Tarea',
    SUBSTR(t.titulo, 1, 40) as 'Título',
    u.username as 'Usuario',
    SUBSTR(e.creado_en, 1, 16) as 'Fecha'
FROM backlog_evidencia e
INNER JOIN backlog_tarea t ON e.tarea_id = t.id
LEFT JOIN auth_user u ON e.creado_por_id = u.id
WHERE t.sprint_id = $SPRINT_ID
ORDER BY e.creado_en DESC
LIMIT 10;

SELECT '' as '';
EOF

# 4. TAREAS CRÍTICAS (sin avance)
echo -e "${BLUE}⚠️  Identificando tareas críticas...${NC}"
sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT '=== TAREAS SIN INICIAR (TOP 10) ===' as '';
SELECT 
    t.id as 'ID',
    SUBSTR(t.titulo, 1, 50) as 'Título',
    COALESCE(u.username, 'SIN ASIGNAR') as 'Asignado',
    t.esfuerzo_sp as 'SP',
    t.categoria as 'Cat'
FROM backlog_tarea t
LEFT JOIN backlog_integrante i ON t.asignado_a_id = i.id
LEFT JOIN auth_user u ON i.user_id = u.id
WHERE t.sprint_id = $SPRINT_ID 
  AND t.estado = 'NUEVO'
ORDER BY t.esfuerzo_sp DESC
LIMIT 10;

SELECT '' as '';
EOF

# 5. TAREAS COMPLETADAS RECIENTEMENTE
echo -e "${BLUE}✅ Listando tareas completadas...${NC}"
sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT '=== TAREAS APROBADAS ===' as '';
SELECT 
    t.id as 'ID',
    SUBSTR(t.titulo, 1, 50) as 'Título',
    u.username as 'Usuario',
    t.fecha_cierre as 'Fecha Cierre',
    t.esfuerzo_sp as 'SP'
FROM backlog_tarea t
LEFT JOIN backlog_integrante i ON t.asignado_a_id = i.id
LEFT JOIN auth_user u ON i.user_id = u.id
WHERE t.sprint_id = $SPRINT_ID 
  AND t.estado = 'APROBADO'
ORDER BY t.fecha_cierre DESC;

SELECT '' as '';
EOF

# 6. TAREAS POR CATEGORÍA
echo -e "${BLUE}📁 Analizando por categoría...${NC}"
sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT '=== DISTRIBUCIÓN POR CATEGORÍA ===' as '';
SELECT 
    categoria as 'Categoría',
    COUNT(*) as 'Total',
    SUM(CASE WHEN estado = 'APROBADO' THEN 1 ELSE 0 END) as 'Completas',
    COALESCE(SUM(esfuerzo_sp), 0) as 'SP'
FROM backlog_tarea
WHERE sprint_id = $SPRINT_ID
GROUP BY categoria
ORDER BY COUNT(*) DESC;

SELECT '' as '';
EOF

# Agregar conclusión
cat >> "$REPORT_FILE" <<EOF

===============================================
   ANÁLISIS Y RECOMENDACIONES
===============================================
EOF

# Calcular métricas para recomendaciones
TOTAL_TAREAS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_ID;")
TAREAS_COMPLETAS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_ID AND estado = 'APROBADO';")
TAREAS_SIN_EVIDENCIA=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea t LEFT JOIN backlog_evidencia e ON t.id = e.tarea_id WHERE t.sprint_id = $SPRINT_ID AND e.id IS NULL;")
PORCENTAJE_COMPLETO=$(awk "BEGIN {printf \"%.1f\", ($TAREAS_COMPLETAS / $TOTAL_TAREAS) * 100}")

cat >> "$REPORT_FILE" <<EOF

📊 Métricas Generales:
   - Total de tareas: $TOTAL_TAREAS
   - Tareas completadas: $TAREAS_COMPLETAS ($PORCENTAJE_COMPLETO%)
   - Tareas sin evidencia: $TAREAS_SIN_EVIDENCIA

EOF

# Recomendaciones basadas en métricas
if (( $(echo "$PORCENTAJE_COMPLETO < 30" | bc -l) )); then
    cat >> "$REPORT_FILE" <<EOF
⚠️  ALERTA CRÍTICA:
   El sprint tiene un avance menor al 30%. Se recomienda:
   - Reunión de emergencia con el equipo
   - Identificar bloqueos y resolverlos inmediatamente
   - Considerar reducir el alcance del sprint

EOF
elif (( $(echo "$PORCENTAJE_COMPLETO < 70" | bc -l) )); then
    cat >> "$REPORT_FILE" <<EOF
⚠️  ALERTA MODERADA:
   El avance del sprint es menor al 70%. Se recomienda:
   - Revisar tareas bloqueadas
   - Priorizar tareas críticas
   - Aumentar comunicación del equipo

EOF
else
    cat >> "$REPORT_FILE" <<EOF
✅ PROGRESO SALUDABLE:
   El sprint va por buen camino. Mantener el ritmo.

EOF
fi

cat >> "$REPORT_FILE" <<EOF

===============================================
   FIN DEL REPORTE
===============================================
Archivo generado: $REPORT_FILE
Próxima revisión: $(date -d "next monday" +%Y-%m-%d)
EOF

# 7. GENERAR CSV PARA ANÁLISIS
echo -e "${BLUE}📄 Generando archivo CSV...${NC}"
sqlite3 -header -csv "$DB_PATH" <<EOF > "$CSV_FILE"
SELECT 
    t.id,
    t.titulo,
    t.estado,
    t.categoria,
    t.completada,
    t.esfuerzo_sp,
    COALESCE(u.username, 'SIN_ASIGNAR') as asignado_a,
    i.rol,
    t.fecha_cierre,
    (SELECT COUNT(*) FROM backlog_evidencia WHERE tarea_id = t.id) as cant_evidencias
FROM backlog_tarea t
LEFT JOIN backlog_integrante i ON t.asignado_a_id = i.id
LEFT JOIN auth_user u ON i.user_id = u.id
WHERE t.sprint_id = $SPRINT_ID
ORDER BY t.estado, u.username;
EOF

# 8. GENERAR HTML
echo -e "${BLUE}🌐 Generando reporte HTML...${NC}"

# Obtener datos para el HTML
STATS_DATA=$(sqlite3 "$DB_PATH" <<SQLEOF
SELECT 
    estado,
    COUNT(*) as cantidad,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_ID), 1) as porcentaje,
    COALESCE(SUM(esfuerzo_sp), 0) as sp
FROM backlog_tarea
WHERE sprint_id = $SPRINT_ID
GROUP BY estado;
SQLEOF
)

# Crear archivo HTML
cat > "$HTML_FILE" <<'HTMLSTART'
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte Sprint</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 15px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.2); 
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        header h1 { font-size: 2.5em; margin-bottom: 10px; }
        header p { font-size: 1.1em; opacity: 0.9; }
        .stats-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 20px; 
            margin: 30px 0; 
        }
        .stat-card { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 25px; 
            border-radius: 12px; 
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-card h3 { font-size: 3em; margin-bottom: 10px; }
        .stat-card p { font-size: 1.2em; opacity: 0.9; margin-bottom: 5px; }
        .stat-card small { opacity: 0.8; }
        h2 { 
            color: #2c3e50; 
            margin: 40px 0 20px 0; 
            padding-bottom: 10px; 
            border-bottom: 3px solid #667eea;
            font-size: 1.8em;
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        th, td { 
            padding: 15px; 
            text-align: left; 
        }
        th { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
        }
        tr:nth-child(even) { background: #f8f9fa; }
        tr:hover { background: #e9ecef; }
        .badge { 
            padding: 6px 12px; 
            border-radius: 20px; 
            font-size: 0.85em; 
            font-weight: bold;
            display: inline-block;
        }
        .badge-success { background: #28a745; color: white; }
        .badge-warning { background: #ffc107; color: #333; }
        .badge-danger { background: #dc3545; color: white; }
        .badge-info { background: #17a2b8; color: white; }
        .badge-secondary { background: #6c757d; color: white; }
        .footer { 
            margin-top: 40px; 
            padding-top: 20px; 
            border-top: 2px solid #dee2e6; 
            text-align: center; 
            color: #6c757d; 
        }
        .footer p { margin: 5px 0; }
        .alert {
            padding: 15px;
            margin: 20px 0;
            border-radius: 8px;
            border-left: 4px solid;
        }
        .alert-success { background: #d4edda; border-color: #28a745; color: #155724; }
        .alert-warning { background: #fff3cd; border-color: #ffc107; color: #856404; }
        .alert-danger { background: #f8d7da; border-color: #dc3545; color: #721c24; }
        .download-buttons {
            text-align: center;
            margin: 30px 0;
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            margin: 0 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Reporte Semanal Sprint</h1>
HTMLSTART

# Agregar información del sprint al HTML
cat >> "$HTML_FILE" <<HTMLINFO
            <p><strong>Sprint:</strong> $SPRINT_NAME | <strong>Período:</strong> $SPRINT_START → $SPRINT_END</p>
            <p><strong>Generado:</strong> $DATETIME</p>
        </header>

        <h2>📈 Resumen General</h2>
        <div class="stats-grid">
HTMLINFO

# Agregar estadísticas al HTML
echo "$STATS_DATA" | while IFS='|' read estado cantidad porcentaje sp; do
    if [ -n "$estado" ] && [ "$estado" != "estado" ]; then
        cat >> "$HTML_FILE" <<STATCARD
            <div class="stat-card">
                <h3>$cantidad</h3>
                <p>$estado</p>
                <small>$porcentaje% | $sp SP</small>
            </div>
STATCARD
    fi
done

# Agregar alert basado en progreso
if (( $(echo "$PORCENTAJE_COMPLETO < 30" | bc -l) )); then
    ALERT_CLASS="alert-danger"
    ALERT_MSG="⚠️ ALERTA CRÍTICA: El sprint tiene un avance menor al 30%"
elif (( $(echo "$PORCENTAJE_COMPLETO < 70" | bc -l) )); then
    ALERT_CLASS="alert-warning"
    ALERT_MSG="⚠️ Alerta: El avance del sprint requiere atención"
else
    ALERT_CLASS="alert-success"
    ALERT_MSG="✅ El sprint va por buen camino"
fi

# Finalizar HTML
cat >> "$HTML_FILE" <<HTMLEND
        </div>

        <div class="alert $ALERT_CLASS">
            <strong>$ALERT_MSG</strong><br>
            Progreso: $PORCENTAJE_COMPLETO% ($TAREAS_COMPLETAS de $TOTAL_TAREAS tareas completadas)
        </div>

        <h2>📥 Descargar Reportes</h2>
        <div class="download-buttons">
            <a href="$(basename $REPORT_FILE)" class="btn" download>📄 Descargar TXT</a>
            <a href="$(basename $CSV_FILE)" class="btn" download>📊 Descargar CSV</a>
        </div>

        <div class="footer">
            <p><strong>NEUSI DevOps Team</strong></p>
            <p>Sistema de Gestión de Tareas | Generado automáticamente</p>
            <p>Próxima revisión: $(date -d "next monday" +%Y-%m-%d)</p>
        </div>
    </div>
</body>
</html>
HTMLEND

# Mostrar resumen en consola
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✅ Reportes generados exitosamente${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "📄 Reporte TXT: ${YELLOW}$REPORT_FILE${NC}"
echo -e "📊 Reporte CSV: ${YELLOW}$CSV_FILE${NC}"
echo -e "🌐 Reporte HTML: ${YELLOW}$HTML_FILE${NC}"
echo ""
echo -e "📊 Resumen:"
echo -e "   - Total tareas: ${YELLOW}$TOTAL_TAREAS${NC}"
echo -e "   - Completadas: ${GREEN}$TAREAS_COMPLETAS${NC} (${PORCENTAJE_COMPLETO}%)"
echo -e "   - Sin evidencia: ${RED}$TAREAS_SIN_EVIDENCIA${NC}"
echo ""

# Mostrar preview del reporte
echo -e "${BLUE}📋 Preview del reporte:${NC}"
echo -e "${BLUE}───────────────────────────────────────${NC}"
head -n 40 "$REPORT_FILE"
echo -e "${BLUE}───────────────────────────────────────${NC}"
echo -e "${YELLOW}... (ver archivo completo en $REPORT_FILE)${NC}"
echo ""

echo -e "${GREEN}✨ Script finalizado correctamente${NC}"
echo ""
