from datetime import date
from backlog.models import Tarea, Sprint, Integrante

# 1. Eliminar todas las tareas previas
print("🗑️ Eliminando todas las tareas del backlog...")
Tarea.objects.all().delete()

# 2. Crear sprint por defecto (22–29 septiembre 2025)
sprint, _ = Sprint.objects.get_or_create(
    inicio=date(2025, 9, 22),
    fin=date(2025, 9, 29)
)
print(f"📌 Usando Sprint {sprint.id}: {sprint.inicio} → {sprint.fin}")

# 3. Definir tareas completas de la semana 22 SEP - 29 con criterios de aceptación
tareas_por_integrante = {
    "laura": [
        {
            "titulo": "CUENTAS DE COBRO",
            "descripcion": "Generar y gestionar las cuentas de cobro pendientes del período",
            "criterios": "- Todas las facturas del período procesadas\n- Archivo Excel con seguimiento actualizado\n- Envío de cuentas a clientes confirmado\n- Registro de pagos recibidos",
            "categoria": "UI"
        },
        {
            "titulo": "BOTON PSE",
            "descripcion": "Implementar y configurar botón de pago PSE en el sistema",
            "criterios": "- Botón PSE integrado y funcionando\n- Pruebas de pago realizadas satisfactoriamente\n- Documentación técnica completada\n- Configuración de seguridad validada",
            "categoria": "NUI"
        },
        {
            "titulo": "GESTIONAR CAMARA DE COMERCIO ANDRES",
            "descripcion": "Tramitar documentación de cámara de comercio para Andrés",
            "criterios": "- Documentos requeridos reunidos\n- Trámite iniciado en cámara de comercio\n- Seguimiento documentado\n- Certificados obtenidos",
            "categoria": "UNI"
        },
        {
            "titulo": "GESTION DE RECIBOS Y SOPORTES",
            "descripcion": "Organizar y archivar recibos y soportes contables",
            "criterios": "- Recibos clasificados por categoría\n- Archivo digital organizado\n- Base de datos actualizada\n- Respaldos de seguridad realizados",
            "categoria": "UI"
        }
    ],
    "diana": [
        {
            "titulo": "ELABORAR Y GESTIONAR REDES SOCIALES",
            "descripcion": "Crear contenido y gestionar presencia en redes sociales de NEUSI",
            "criterios": "- Calendario de contenido semanal creado\n- Publicaciones programadas\n- Métricas de engagement monitoreadas\n- Respuestas a comentarios gestionadas",
            "categoria": "NUI"
        },
        {
            "titulo": "PLANTILLA DE WEB DE NEUSI",
            "descripcion": "Diseñar plantilla web corporativa para NEUSI",
            "criterios": "- Diseño responsive completado\n- Aprobación del cliente obtenida\n- Archivos fuente entregados\n- Optimización SEO básica implementada",
            "categoria": "UI"
        },
        {
            "titulo": "INDICADORES DE GESTION",
            "descripcion": "Desarrollar dashboard de indicadores de gestión",
            "criterios": "- KPIs definidos y documentados\n- Dashboard funcional creado\n- Reportes automatizados configurados\n- Validación de datos con áreas responsables",
            "categoria": "NUI"
        },
        {
            "titulo": "CUENTAS DE BOTS",
            "descripcion": "Configurar y gestionar cuentas de bots automatizados",
            "criterios": "- Cuentas creadas y configuradas\n- Automatización funcionando correctamente\n- Documentación de accesos completada\n- Monitoreo de funcionamiento establecido",
            "categoria": "NUNI"
        },
        {
            "titulo": "GESTIONAR INSTALACION DE OFICINA DE IMPRESIONES",
            "descripcion": "Coordinar instalación de equipos de impresión en oficina",
            "criterios": "- Equipos instalados y configurados\n- Pruebas de funcionamiento realizadas\n- Personal capacitado en uso\n- Procedimientos de mantenimiento documentados",
            "categoria": "UNI"
        },
        {
            "titulo": "CONCRETAR FLUJO DE TRABAJO CON LAURA",
            "descripcion": "Definir y documentar flujo de trabajo conjunto con Laura",
            "criterios": "- Reunión de alineación realizada\n- Flujo documentado y aprobado\n- Roles y responsabilidades definidos claramente\n- Cronograma de actividades establecido",
            "categoria": "UI"
        }
    ],
    "daniel": [
        {
            "titulo": "INDICADORES FINANCIERA MODULO FINANICERA POWER BI",
            "descripcion": "Desarrollar indicadores financieros en módulo Power BI",
            "criterios": "- Dashboard financiero creado y funcional\n- Conexión a fuentes de datos establecida\n- Métricas validadas con contabilidad\n- Actualización automática configurada",
            "categoria": "UI"
        },
        {
            "titulo": "ETL DE PRESUPUESTO Y CUPOS DE CREDITO",
            "descripcion": "Implementar proceso ETL para presupuestos y cupos de crédito",
            "criterios": "- Proceso ETL funcionando automáticamente\n- Datos validados contra fuente original\n- Documentación técnica completa\n- Manejo de errores implementado",
            "categoria": "UI"
        },
        {
            "titulo": "PROGRAMACION DE INDICADORES MODULO CARTERA (INTEGRACION API MODULO CARTERA)",
            "descripcion": "Programar indicadores del módulo de cartera con integración API",
            "criterios": "- API de cartera integrada exitosamente\n- Indicadores programados y funcionando\n- Pruebas de integración completadas\n- Documentación de API actualizada",
            "categoria": "UI"
        },
        {
            "titulo": "CARGA DATA DE CREDITO",
            "descripcion": "Cargar y procesar datos históricos de crédito",
            "criterios": "- Datos históricos cargados completamente\n- Proceso de validación ejecutado\n- Respaldos configurados\n- Integridad de datos verificada",
            "categoria": "UNI"
        },
        {
            "titulo": "MODULO FINANZAPP DE GESTION DE INGRESOS Y EGRESOS",
            "descripcion": "Desarrollar módulo para gestión de ingresos y egresos",
            "criterios": "- Módulo desarrollado y funcional\n- Integración con sistema contable\n- Pruebas de usuario completadas\n- Reportes de flujo de caja implementados",
            "categoria": "NUI"
        },
        {
            "titulo": "PROTOTIPO DEVOPS NEUSI",
            "descripcion": "Crear prototipo de infraestructura DevOps para NEUSI",
            "criterios": "- Pipeline CI/CD básico funcionando\n- Documentación de arquitectura\n- Ambiente de pruebas configurado\n- Monitoreo básico implementado",
            "categoria": "NUNI"
        },
        {
            "titulo": "MANTENIMIENTO SERVIDORES",
            "descripcion": "Realizar mantenimiento preventivo de servidores",
            "criterios": "- Actualizaciones de seguridad aplicadas\n- Respaldos verificados y funcionando\n- Monitoreo de performance activo\n- Documentación de cambios actualizada",
            "categoria": "UNI"
        }
    ],
    "samir": [
        {
            "titulo": "INTEGRACION Y CARGA DE TALENTO Y CULTURA",
            "descripcion": "Integrar módulo de talento y cultura al sistema principal",
            "criterios": "- Módulo integrado al sistema principal\n- Datos migrados correctamente\n- Pruebas de integración completadas\n- Documentación técnica actualizada",
            "categoria": "UI"
        },
        {
            "titulo": "BACKEND DE APLICATIVO DE LOS MODULOS FINANCIERA, TALENTO Y CULTURA, CARTERA",
            "descripcion": "Desarrollar backend unificado para módulos principales",
            "criterios": "- APIs de todos los módulos desarrolladas\n- Integración entre módulos completada\n- Documentación técnica de APIs\n- Pruebas de carga realizadas",
            "categoria": "UI"
        }
    ],
    "christiam": [
        {
            "titulo": "MODULO CARTERA",
            "descripcion": "Desarrollar frontend del módulo de cartera",
            "criterios": "- Interfaz de usuario funcional y completa\n- Integración con backend exitosa\n- Pruebas de usabilidad realizadas\n- Responsive design implementado",
            "categoria": "UI"
        },
        {
            "titulo": "MODULO DE TALENTO Y CULTURA",
            "descripcion": "Desarrollar frontend del módulo de talento y cultura",
            "criterios": "- Componentes de UI desarrollados\n- Validaciones de formularios implementadas\n- Responsive design completado\n- Integración con backend funcional",
            "categoria": "UI"
        },
        {
            "titulo": "MODULO DE FINANCIERA AGREGAR BOTON CARGA DE ARCHIVO PRESUPUESTO Y CUPOS DE CREDITO",
            "descripcion": "Implementar funcionalidad de carga de archivos en módulo financiero",
            "criterios": "- Botón de carga implementado\n- Validación de tipos de archivo\n- Feedback visual al usuario\n- Procesamiento de archivos exitoso",
            "categoria": "NUI"
        }
    ],
    "juan": [
        {
            "titulo": "ASIGNA CHRISTIAM",
            "descripcion": "Recibir y ejecutar tareas asignadas por Christiam",
            "criterios": "- Tareas definidas claramente por Christiam\n- Cronograma establecido y acordado\n- Recursos necesarios identificados\n- Seguimiento de progreso documentado",
            "categoria": "NUNI"
        }
    ],
    "diego_ortiz": [
        {
            "titulo": "DASHBOARD DE TALENTO Y CULTURA",
            "descripcion": "Crear dashboard de Business Intelligence para talento y cultura",
            "criterios": "- Dashboard funcional en Power BI\n- KPIs de talento implementados\n- Reportes automatizados configurados\n- Validación de datos con RRHH",
            "categoria": "NUI"
        }
    ],
    "andres_gonzalez": [
        {
            "titulo": "DASHBOARD CREDITO",
            "descripcion": "Desarrollar dashboard de crédito en Power BI",
            "criterios": "- Dashboard de crédito creado\n- Métricas de cartera implementadas\n- Alertas de riesgo configuradas\n- Integración con fuentes de datos",
            "categoria": "NUI"
        }
    ],
    "daniela": [
        {
            "titulo": "CORRECIONES DE FORMA FINANCIERA",
            "descripcion": "Realizar correcciones en formularios del módulo financiero",
            "criterios": "- Formularios corregidos según especificaciones\n- Validaciones actualizadas\n- Pruebas de funcionamiento realizadas\n- Documentación de cambios actualizada",
            "categoria": "UNI"
        },
        {
            "titulo": "ESQUELETO DE CREDITO Y CARTERA",
            "descripcion": "Crear estructura base para módulos de crédito y cartera",
            "criterios": "- Estructura de datos definida\n- Componentes base creados\n- Documentación de arquitectura\n- Validación con equipo técnico",
            "categoria": "NUI"
        }
    ],
    "andres_gomez": [
        {
            "titulo": "PLANING DE OFICIAL DE CUMPLIMIENTO",
            "descripcion": "Planificación estratégica para rol de oficial de cumplimiento",
            "criterios": "- Plan estratégico definido\n- Cronograma de implementación establecido\n- Recursos identificados y asignados\n- Marco regulatorio documentado",
            "categoria": "NUI"
        },
        {
            "titulo": "PROGRAMA ACADEMICO DE CURSO DE BI",
            "descripcion": "Desarrollar programa académico para curso de Business Intelligence",
            "criterios": "- Currículo académico definido\n- Materiales de estudio preparados\n- Cronograma de clases establecido\n- Sistema de evaluación implementado",
            "categoria": "NUNI"
        },
        {
            "titulo": "GESTION DE CANALES DE COMUNICACIÓN",
            "descripcion": "Organizar y gestionar canales de comunicación del equipo",
            "criterios": "- Canales organizados por proyecto\n- Procesos de comunicación documentados\n- Responsables asignados por canal\n- Protocolos de escalamiento definidos",
            "categoria": "UNI"
        },
        {
            "titulo": "MANUALES DE PROCESOS Y REPORTES",
            "descripcion": "Crear y actualizar manuales de procesos y reportes",
            "criterios": "- Manuales actualizados y revisados\n- Procesos documentados paso a paso\n- Formatos estandarizados\n- Versiones controladas y distribuidas",
            "categoria": "NUI"
        },
        {
            "titulo": "RETOMAR CONGENTE Y LLAMAR A UNICOOP",
            "descripcion": "Gestión de contactos comerciales con Congente y Unicoop",
            "criterios": "- Contactos retomados exitosamente\n- Reuniones programadas y realizadas\n- Seguimiento comercial documentado\n- Oportunidades identificadas",
            "categoria": "UNI"
        },
        {
            "titulo": "GESTION DE CORREOS CORPORATIVO",
            "descripcion": "Administración de sistema de correos corporativos",
            "criterios": "- Cuentas de correo configuradas\n- Políticas de uso implementadas\n- Seguridad y respaldos verificados\n- Capacitación a usuarios completada",
            "categoria": "UNI"
        }
    ],
    "diego_gomez": [
        {
            "titulo": "FUNCIONAMIENTO DE LAS IMPRESORAS 3 MAQUINAS",
            "descripcion": "Asegurar operación correcta de las 3 impresoras 3D",
            "criterios": "- Las 3 máquinas funcionando correctamente\n- Mantenimiento preventivo al día\n- Operadores capacitados\n- Inventario de materiales controlado",
            "categoria": "UI"
        },
        {
            "titulo": "DOCUMENTACION DE MANTENIMIENTO",
            "descripcion": "Crear manual de mantenimiento para impresoras 3D",
            "criterios": "- Procedimientos de mantenimiento documentados\n- Cronograma de mantenimiento establecido\n- Lista de repuestos y herramientas\n- Registro de mantenimientos implementado",
            "categoria": "NUI"
        },
        {
            "titulo": "PLAN DE COSTOS",
            "descripcion": "Desarrollar plan de costos para servicios de impresión 3D",
            "criterios": "- Estructura de costos definida y calculada\n- Precios de servicios actualizados\n- Análisis de rentabilidad completado\n- Estrategia de precios documentada",
            "categoria": "NUI"
        }
    ]
}

# 4. Crear tareas en la base de datos
for username, lista_tareas in tareas_por_integrante.items():
    try:
        integrante = Integrante.objects.get(user__username=username)
        for tarea_data in lista_tareas:
            tarea = Tarea.objects.create(
                titulo=tarea_data["titulo"],
                descripcion=tarea_data["descripcion"],
                criterios_aceptacion=tarea_data["criterios"],
                categoria=tarea_data["categoria"],
                completada=False,
                asignado_a=integrante,
                sprint=sprint
            )
            print(f"✅ Tarea creada: {tarea.titulo} → {integrante.user.first_name} "
                  f"({tarea.categoria}) - Sprint {sprint.inicio} → {sprint.fin}")
    except Integrante.DoesNotExist:
        print(f"⚠️ No se encontró integrante con username {username}, se omite.")

print("🎉 Backlog completado con todas las tareas de la semana 22–29 sep 2025.")
print(f"📊 Total de tareas creadas: {Tarea.objects.filter(sprint=sprint).count()}")