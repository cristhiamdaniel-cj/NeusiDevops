#!/bin/bash

##############################################
# Script Universal de Análisis de Sprint
# Uso: ./analizar_sprint.sh [numero_sprint]
# Ejemplo: ./analizar_sprint.sh 1
##############################################

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Configuración
PROJECT_DIR="/home/desarrollo/NeuralWasi/NeusiDevops"
DB_PATH="$PROJECT_DIR/db.sqlite3"
REPORTS_DIR="$PROJECT_DIR/reportes_sprint"
DATE=$(date +%Y-%m-%d)
DATETIME=$(date +"%Y-%m-%d %H:%M:%S")

mkdir -p "$REPORTS_DIR"

# Verificar argumento
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Debes especificar el número de sprint${NC}"
    echo ""
    echo -e "${YELLOW}Uso:${NC}"
    echo -e "  $0 [numero_sprint]"
    echo ""
    echo -e "${YELLOW}Ejemplo:${NC}"
    echo -e "  $0 1    # Analizar Sprint 1"
    echo -e "  $0 2    # Analizar Sprint 2"
    echo ""
    echo -e "${CYAN}Sprints disponibles:${NC}"
    sqlite3 -header -column "$DB_PATH" "SELECT id, nombre, inicio, fin FROM backlog_sprint ORDER BY id;"
    exit 1
fi

SPRINT_NUM=$1

# Verificar que el sprint existe
SPRINT_EXISTS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_sprint WHERE id = $SPRINT_NUM;")
if [ "$SPRINT_EXISTS" -eq 0 ]; then
    echo -e "${RED}❌ Error: Sprint $SPRINT_NUM no existe${NC}"
    echo ""
    echo -e "${CYAN}Sprints disponibles:${NC}"
    sqlite3 -header -column "$DB_PATH" "SELECT id, nombre, inicio, fin FROM backlog_sprint ORDER BY id;"
    exit 1
fi

# Obtener info del sprint
SPRINT_INFO=$(sqlite3 "$DB_PATH" "SELECT id, nombre, inicio, fin FROM backlog_sprint WHERE id = $SPRINT_NUM;")
SPRINT_ID=$(echo "$SPRINT_INFO" | cut -d'|' -f1)
SPRINT_NAME=$(echo "$SPRINT_INFO" | cut -d'|' -f2)
SPRINT_START=$(echo "$SPRINT_INFO" | cut -d'|' -f3)
SPRINT_END=$(echo "$SPRINT_INFO" | cut -d'|' -f4)

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  📊 ANÁLISIS COMPLETO - $SPRINT_NAME${NC}"
echo -e "${CYAN}============================================${NC}"
echo -e "Período: ${YELLOW}$SPRINT_START → $SPRINT_END${NC}"
echo -e "Generado: $DATETIME"
echo ""

# Archivos de salida
REPORT_FILE="$REPORTS_DIR/analisis_sprint${SPRINT_NUM}_${DATE}.txt"
CSV_TAREAS="$REPORTS_DIR/tareas_sprint${SPRINT_NUM}_${DATE}.csv"
CSV_RESUMEN="$REPORTS_DIR/resumen_sprint${SPRINT_NUM}_${DATE}.csv"

# ==============================================
# INICIAR REPORTE
# ==============================================
cat > "$REPORT_FILE" <<EOF
===============================================
   ANÁLISIS COMPLETO - $SPRINT_NAME
===============================================
Período: $SPRINT_START → $SPRINT_END
Generado: $DATETIME
===============================================

EOF

# ==============================================
# 1. RESUMEN GENERAL DEL SPRINT
# ==============================================
echo -e "${BLUE}📊 1. Generando resumen general...${NC}"

TOTAL_TAREAS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM;")
APROBADAS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM AND estado = 'APROBADO';")
EN_PROGRESO=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM AND estado = 'EN_PROGRESO';")
TODO=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM AND estado = 'TODO';")
NUEVO=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM AND estado = 'NUEVO';")
SIN_ASIGNAR=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM AND asignado_a_id IS NULL;")

TOTAL_SP=$(sqlite3 "$DB_PATH" "SELECT COALESCE(SUM(esfuerzo_sp), 0) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM;")
APROBADAS_SP=$(sqlite3 "$DB_PATH" "SELECT COALESCE(SUM(esfuerzo_sp), 0) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM AND estado = 'APROBADO';")

PERSONAS_ASIGNADAS=$(sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT asignado_a_id) FROM backlog_tarea WHERE sprint_id = $SPRINT_NUM AND asignado_a_id IS NOT NULL;")

sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT '=== RESUMEN GENERAL DEL SPRINT ===' as '';
SELECT '' as '';
SELECT 'Sprint' as 'Métrica', '$SPRINT_NAME' as 'Valor'
UNION ALL SELECT 'Período', '$SPRINT_START → $SPRINT_END'
UNION ALL SELECT 'Total de tareas', '$TOTAL_TAREAS'
UNION ALL SELECT 'Tareas aprobadas', '$APROBADAS ($(echo "scale=1; $APROBADAS * 100 / $TOTAL_TAREAS" | bc 2>/dev/null || echo "0")%)'
UNION ALL SELECT 'En progreso', '$EN_PROGRESO'
UNION ALL SELECT 'Por hacer (TODO)', '$TODO'
UNION ALL SELECT 'Nuevas (NUEVO)', '$NUEVO'
UNION ALL SELECT 'Sin asignar', '$SIN_ASIGNAR'
UNION ALL SELECT '---', '---'
UNION ALL SELECT 'Story Points totales', '$TOTAL_SP'
UNION ALL SELECT 'Story Points completados', '$APROBADAS_SP ($(echo "scale=1; $APROBADAS_SP * 100 / $TOTAL_SP" | bc 2>/dev/null || echo "0")%)'
UNION ALL SELECT '---', '---'
UNION ALL SELECT 'Personas asignadas', '$PERSONAS_ASIGNADAS';

SELECT '' as '';
SELECT '' as '';

SELECT '=== DISTRIBUCIÓN POR ESTADO ===' as '';
SELECT 
    estado as 'Estado',
    COUNT(*) as 'Cantidad',
    ROUND(COUNT(*) * 100.0 / $TOTAL_TAREAS, 1) || '%' as 'Porcentaje',
    COALESCE(SUM(esfuerzo_sp), 0) as 'Story Points'
FROM backlog_tarea
WHERE sprint_id = $SPRINT_NUM
GROUP BY estado
ORDER BY COUNT(*) DESC;

SELECT '' as '';
SELECT '' as '';
EOF

# ==============================================
# 2. RESUMEN POR INTEGRANTE
# ==============================================
echo -e "${BLUE}📊 2. Analizando por integrante...${NC}"

sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT '=== RESUMEN POR INTEGRANTE ===' as '';
SELECT '' as '';
SELECT 
    COALESCE(u.username, 'SIN_ASIGNAR') as 'Integrante',
    i.rol as 'Rol',
    COUNT(t.id) as 'Total',
    SUM(CASE WHEN t.estado = 'APROBADO' THEN 1 ELSE 0 END) as '✓ OK',
    SUM(CASE WHEN t.estado = 'EN_PROGRESO' THEN 1 ELSE 0 END) as '⟳ Prog',
    SUM(CASE WHEN t.estado = 'TODO' THEN 1 ELSE 0 END) as '○ TODO',
    SUM(CASE WHEN t.estado = 'NUEVO' THEN 1 ELSE 0 END) as '+ Nuevo',
    COALESCE(SUM(t.esfuerzo_sp), 0) as 'SP Tot',
    SUM(CASE WHEN t.estado = 'APROBADO' THEN COALESCE(t.esfuerzo_sp, 0) ELSE 0 END) as 'SP OK',
    ROUND(
        CAST(SUM(CASE WHEN t.estado = 'APROBADO' THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / 
        COUNT(t.id), 1
    ) || '%' as '% Éxito'
FROM backlog_tarea t
LEFT JOIN backlog_integrante i ON t.asignado_a_id = i.id
LEFT JOIN auth_user u ON i.user_id = u.id
WHERE t.sprint_id = $SPRINT_NUM
GROUP BY u.username, i.rol, u.id
ORDER BY 
    SUM(CASE WHEN t.estado = 'APROBADO' THEN 1 ELSE 0 END) DESC,
    u.username;

SELECT '' as '';
SELECT '' as '';
EOF

# ==============================================
# 3. TAREAS DETALLADAS POR PERSONA
# ==============================================
echo -e "${BLUE}📋 3. Generando detalle por persona...${NC}"

cat >> "$REPORT_FILE" <<EOF
===============================================
   DETALLE COMPLETO DE TAREAS POR PERSONA
===============================================

EOF

# Obtener lista de personas con tareas
PERSONAS=$(sqlite3 "$DB_PATH" "
SELECT DISTINCT COALESCE(u.username, 'SIN_ASIGNAR')
FROM backlog_tarea t
LEFT JOIN backlog_integrante i ON t.asignado_a_id = i.id
LEFT JOIN auth_user u ON i.user_id = u.id
WHERE t.sprint_id = $SPRINT_NUM
ORDER BY u.username;
")

CONTADOR=1
TOTAL_PERSONAS=$(echo "$PERSONAS" | wc -l)

for persona in $PERSONAS; do
    echo -e "${CYAN}   → [$CONTADOR/$TOTAL_PERSONAS] $persona${NC}"
    
    if [ "$persona" = "SIN_ASIGNAR" ]; then
        cat >> "$REPORT_FILE" <<EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 TAREAS SIN ASIGNAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF
        
        sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT 
    t.id as 'ID',
    SUBSTR(t.titulo, 1, 60) as 'Título',
    t.estado as 'Estado',
    t.categoria as 'Cat',
    COALESCE(t.esfuerzo_sp, 0) as 'SP',
    CASE 
        WHEN EXISTS(SELECT 1 FROM backlog_evidencia WHERE tarea_id = t.id) 
        THEN '✓' 
        ELSE '✗' 
    END as 'Evid'
FROM backlog_tarea t
WHERE t.sprint_id = $SPRINT_NUM 
  AND t.asignado_a_id IS NULL
ORDER BY t.estado, t.id;
EOF
    else
        # Obtener estadísticas de la persona
        PERSONA_STATS=$(sqlite3 "$DB_PATH" "
        SELECT 
            COUNT(*),
            SUM(CASE WHEN estado = 'APROBADO' THEN 1 ELSE 0 END),
            SUM(CASE WHEN estado = 'EN_PROGRESO' THEN 1 ELSE 0 END),
            SUM(CASE WHEN estado IN ('TODO', 'NUEVO') THEN 1 ELSE 0 END),
            COALESCE(SUM(esfuerzo_sp), 0)
        FROM backlog_tarea t
        INNER JOIN backlog_integrante i ON t.asignado_a_id = i.id
        INNER JOIN auth_user u ON i.user_id = u.id
        WHERE t.sprint_id = $SPRINT_NUM AND u.username = '$persona';
        ")
        
        P_TOTAL=$(echo "$PERSONA_STATS" | cut -d'|' -f1)
        P_OK=$(echo "$PERSONA_STATS" | cut -d'|' -f2)
        P_PROG=$(echo "$PERSONA_STATS" | cut -d'|' -f3)
        P_PEND=$(echo "$PERSONA_STATS" | cut -d'|' -f4)
        P_SP=$(echo "$PERSONA_STATS" | cut -d'|' -f5)
        
        cat >> "$REPORT_FILE" <<EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 $persona
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: $P_TOTAL tareas | OK: $P_OK | Progreso: $P_PROG | Pendientes: $P_PEND | SP: $P_SP

EOF

        sqlite3 -header -column "$DB_PATH" <<EOF >> "$REPORT_FILE"
.mode column
.headers on

SELECT 
    t.id as 'ID',
    SUBSTR(t.titulo, 1, 60) as 'Título',
    t.estado as 'Estado',
    t.categoria as 'Cat',
    COALESCE(t.esfuerzo_sp, 0) as 'SP',
    CASE 
        WHEN EXISTS(SELECT 1 FROM backlog_evidencia WHERE tarea_id = t.id) 
        THEN '✓' 
        ELSE '✗' 
    END as 'Evid'
FROM backlog_tarea t
INNER JOIN backlog_integrante i ON t.asignado_a_id = i.id
INNER JOIN auth_user u ON i.user_id = u.id
WHERE t.sprint_id = $SPRINT_NUM 
  AND u.username = '$persona'
ORDER BY 
    CASE t.estado
        WHEN 'APROBADO' THEN 1
        WHEN 'EN_PROGRESO' THEN 2
        WHEN 'TODO' THEN 3
        WHEN 'NUEVO' THEN 4
        ELSE 5
    END,
    t.id;
EOF
    fi
    
    cat >> "$REPORT_FILE" <<EOF


EOF
    CONTADOR=$((CONTADOR + 1))
done

# ==============================================
# 4. GENERAR CSV DE TODAS LAS TAREAS
# ==============================================
echo -e "${BLUE}📊 4. Generando CSV de tareas...${NC}"

sqlite3 -header -csv "$DB_PATH" <<EOF > "$CSV_TAREAS"
SELECT 
    t.id as 'ID',
    COALESCE(u.username, 'SIN_ASIGNAR') as 'Asignado_A',
    i.rol as 'Rol',
    t.titulo as 'Titulo',
    t.descripcion as 'Descripcion',
    t.estado as 'Estado',
    t.categoria as 'Categoria',
    COALESCE(t.esfuerzo_sp, 0) as 'Story_Points',
    CASE 
        WHEN EXISTS(SELECT 1 FROM backlog_evidencia WHERE tarea_id = t.id) 
        THEN 'SI' 
        ELSE 'NO' 
    END as 'Tiene_Evidencia',
    (SELECT COUNT(*) FROM backlog_evidencia WHERE tarea_id = t.id) as 'Cant_Evidencias',
    t.fecha_cierre as 'Fecha_Cierre',
    t.criterios_aceptacion as 'Criterios_Aceptacion'
FROM backlog_tarea t
LEFT JOIN backlog_integrante i ON t.asignado_a_id = i.id
LEFT JOIN auth_user u ON i.user_id = u.id
WHERE t.sprint_id = $SPRINT_NUM
ORDER BY u.username, t.estado, t.id;
EOF

# ==============================================
# 5. GENERAR CSV RESUMEN POR PERSONA
# ==============================================
echo -e "${BLUE}📊 5. Generando CSV resumen...${NC}"

sqlite3 -header -csv "$DB_PATH" <<EOF > "$CSV_RESUMEN"
SELECT 
    COALESCE(u.username, 'SIN_ASIGNAR') as 'Integrante',
    i.rol as 'Rol',
    COUNT(t.id) as 'Total_Tareas',
    SUM(CASE WHEN t.estado = 'APROBADO' THEN 1 ELSE 0 END) as 'Aprobadas',
    SUM(CASE WHEN t.estado = 'EN_PROGRESO' THEN 1 ELSE 0 END) as 'En_Progreso',
    SUM(CASE WHEN t.estado = 'TODO' THEN 1 ELSE 0 END) as 'TODO',
    SUM(CASE WHEN t.estado = 'NUEVO' THEN 1 ELSE 0 END) as 'NUEVO',
    COALESCE(SUM(t.esfuerzo_sp), 0) as 'SP_Total',
    SUM(CASE WHEN t.estado = 'APROBADO' THEN COALESCE(t.esfuerzo_sp, 0) ELSE 0 END) as 'SP_Completados',
    ROUND(
        CAST(SUM(CASE WHEN t.estado = 'APROBADO' THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / 
        COUNT(t.id), 1
    ) as 'Porcentaje_Exito',
    COUNT(DISTINCT e.id) as 'Total_Evidencias'
FROM backlog_tarea t
LEFT JOIN backlog_integrante i ON t.asignado_a_id = i.id
LEFT JOIN auth_user u ON i.user_id = u.id
LEFT JOIN backlog_evidencia e ON t.id = e.tarea_id
WHERE t.sprint_id = $SPRINT_NUM
GROUP BY u.username, i.rol, u.id
ORDER BY u.username;
EOF

# ==============================================
# FINALIZAR REPORTE
# ==============================================
cat >> "$REPORT_FILE" <<EOF

===============================================
   FIN DEL ANÁLISIS
===============================================
Sprint analizado: $SPRINT_NAME
Archivos generados:
  📄 Reporte completo: $REPORT_FILE
  📊 CSV tareas: $CSV_TAREAS
  📊 CSV resumen: $CSV_RESUMEN

Fecha: $DATETIME
===============================================
EOF

# ==============================================
# MOSTRAR RESUMEN EN CONSOLA
# ==============================================
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✅ Análisis completado${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${YELLOW}Sprint: $SPRINT_NAME${NC}"
echo -e "Período: $SPRINT_START → $SPRINT_END"
echo ""
echo -e "${CYAN}📊 RESUMEN:${NC}"
echo -e "   Total tareas: ${BOLD}$TOTAL_TAREAS${NC}"
echo -e "   ${GREEN}✓ Aprobadas: $APROBADAS${NC} ($(echo "scale=1; $APROBADAS * 100 / $TOTAL_TAREAS" | bc 2>/dev/null || echo "0")%)"
echo -e "   ${YELLOW}⟳ En progreso: $EN_PROGRESO${NC}"
echo -e "   ${RED}○ Pendientes: $((TODO + NUEVO))${NC}"
echo -e "   ${MAGENTA}⚠ Sin asignar: $SIN_ASIGNAR${NC}"
echo ""
echo -e "   Story Points: ${BOLD}$APROBADAS_SP / $TOTAL_SP${NC} ($(echo "scale=1; $APROBADAS_SP * 100 / $TOTAL_SP" | bc 2>/dev/null || echo "0")%)"
echo -e "   Personas asignadas: ${BOLD}$PERSONAS_ASIGNADAS${NC}"
echo ""
echo -e "${CYAN}📁 ARCHIVOS GENERADOS:${NC}"
echo -e "   📄 ${YELLOW}$REPORT_FILE${NC}"
echo -e "   📊 ${YELLOW}$CSV_TAREAS${NC}"
echo -e "   📊 ${YELLOW}$CSV_RESUMEN${NC}"
echo ""
echo -e "${BLUE}Para ver el reporte completo:${NC}"
echo -e "   cat $REPORT_FILE"
echo ""
echo -e "${BLUE}Para abrir el CSV:${NC}"
echo -e "   libreoffice $CSV_TAREAS"
echo ""
