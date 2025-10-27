**NEUSI DevOps - Documentación de Dependencias Frontend ⇄ Backend (v1.1 extendida)**

**Responsable: Juan Carlos Santamaria**

**2025**

**Introducción**

El presente documento constituye una guía técnica exhaustiva que detalla las relaciones y dependencias existentes entre los componentes del **frontend** y el **backend** del proyecto **NEUSI Task Manager**, desarrollado en el marco de la metodología DevOps. Su propósito es garantizar la trazabilidad y comprensión integral de cómo los archivos de interfaz de usuario (HTML, CSS y JavaScript) interactúan con las vistas, controladores y modelos del backend construido en **Django**. Esta documentación sirve como una referencia para desarrolladores, diseñadores y administradores del sistema, asegurando la coherencia en el mantenimiento, evolución y expansión de las funcionalidades del sistema.

En este contexto, el documento no se limita únicamente a describir dependencias técnicas, sino que también abarca la estructura visual, los principios de diseño, la arquitectura de componentes reutilizables y la gestión de estilos bajo un enfoque coherente y escalable. Se hace énfasis en los aspectos estéticos del frontend -particularmente la paleta de colores, sombras, tipografía y transiciones-, así como en las funciones JavaScript y validaciones HTML que complementan la experiencia de usuario. De esta forma, el documento proporciona una visión 360° del ecosistema de desarrollo de NEUSI Task Manager.

**1) Alcance y arquitectura del frontend**

El **frontend** de NEUSI Task Manager fue diseñado con un enfoque modular, altamente estructurado y orientado a la reutilización de componentes. Todas las vistas están construidas utilizando el sistema de plantillas de **Django**, lo que permite la inyección dinámica de datos provenientes del backend mediante contexto y etiquetas de renderizado. Cada sección de la interfaz Backlog, Kanban, Dailys, Cierre de tareas y Confirmaciones cuenta con su propio archivo .html y un archivo de estilos CSS independiente dentro del directorio static/backlog/, lo cual facilita la mantenibilidad y coherencia visual.

La arquitectura del frontend sigue los principios de separación de responsabilidades: el HTML define la estructura semántica, el CSS establece el estilo visual y el JavaScript se encarga de la interactividad. Se emplea **Bootstrap 5.3** como base para los componentes, adaptado mediante una capa personalizada de estilos para mantener la identidad visual de NEUSI. Esta identidad se caracteriza por un diseño limpio, moderno y enfocado en la legibilidad, con una tipografía principal basada en system-ui, Roboto y Arial, y un uso estratégico de colores en escala lila y coral para reforzar la marca.

El objetivo principal del frontend es proporcionar una experiencia fluida, responsiva y visualmente coherente, con elementos adaptables a diferentes resoluciones y dispositivos. Las tarjetas, tablas y formularios mantienen un patrón visual consistente: bordes redondeados (border-radius: 16px), sombras suaves (box-shadow: 0 10px 28px rgba (16,24,40,.12)), y gradientes lineales que dan profundidad y ligereza a la interfaz.

**Paleta cromática (en hexadecimal)**

La paleta de NEUSI no solo cumple un propósito estético, sino también funcional. Los colores están cuidadosamente seleccionados para representar jerarquías de información, estados del sistema y niveles de alerta. A continuación, se presenta el desglose detallado:

| **Nombre** | **Descripción** | **Código Hexadecimal** | **Uso principal** |
| --- | --- | --- | --- |
| **Morado profundo** | Color institucional base que comunica confianza y profesionalismo. | #3B0764 | Encabezados, títulos y bordes activos. |
| **Morado principal** | Acento visual dominante que refuerza la identidad del sistema. | #6D28D9 | Botones primarios, íconos destacados y enlaces principales. |
| **Coral** | Color cálido utilizado para captar la atención o señalar errores. | #FF7A7A | Alertas, validaciones erróneas y mensajes críticos. |
| **Azul primario** | Tono neutro que complementa el esquema principal y mejora la legibilidad. | #007BFF | Botones secundarios, enlaces de navegación y tarjetas informativas. |
| **Verde éxito** | Representa confirmaciones, logros y operaciones exitosas. | #28A745 | Estados de finalización, etiquetas de éxito y alertas positivas. |
| **Rojo error** | Señala peligro, eliminación o acciones irreversibles. | #DC3545 | Botones de eliminación, avisos críticos, alertas de error. |
| **Gris neutro** | Equilibrio visual, empleado en fondos secundarios o textos atenuados. | #6C757D | Textos de apoyo, bordes pasivos y elementos deshabilitados. |
| **Amarillo advertencia** | Contraste cálido para resaltar información relevante. | #FFC107 | Advertencias, formularios incompletos y recordatorios. |
| **Fondo base (niebla lila)** | Base cromática que transmite suavidad y calma. | #F4EFFF | Fondo principal del sitio, áreas neutras y secciones no interactivas. |

Estas tonalidades se declaran en todas las variables dentro de los archivos CSS para permitir ajustes globales de color y facilitar el mantenimiento de la coherencia visual entre los distintos módulos.

**2) Mapa de dependencias general**

El siguiente mapa resume la relación entre los templates del frontend, las vistas del backend y los modelos involucrados. Este esquema ayuda a visualizar el flujo de información entre las capas del sistema:

| **Template (Frontend)** | **Vista (Backend)** | **Modelos / URLs** | **CSS / JS / Frameworks** |
| --- | --- | --- | --- |
| kanban_board.html | kanban_board(request) | Tarea, Epica, Sprint, URL /tarea/&lt;id&gt;/cambiar-estado/ | Bootstrap 5.3, kanban.css, Drag & Drop JS. |
| backlog_lista.html | backlog_lista(request) | Tarea, Epica, Sprint, Integrante | backlog.css, Filtros dinámicos, modales Bootstrap. |
| daily_resumen.html | daily_resumen(request) | Daily, Integrante | daily-resumen.css, tabla responsiva, confirmaciones JS. |
| tarea_close.html | cerrar_tarea (request, id) | Tarea (informe_cierre) | tarea_close.css, validación HTML5, botones y formularios de carga. |
| confirm_delete.html | eliminar_\* (genérico) | Tarea, Sprint, Daily | confirm-delete.css, alertas visuales rojas. |

**3) Descripción de relaciones Frontend ⇄ Backend**

**3.1 Kanban Board - Interactividad y actualización de estados**

El **Kanban Board** constituye el núcleo visual del sistema de gestión de tareas. En el frontend, la vista kanban_board.html organiza las tareas en columnas según su estado (Pendiente, En progreso, Completada, Bloqueada). Cada tarjeta incluye el título, responsable, categoría y sprint. La interactividad es gestionada por JavaScript nativo mediante eventos de **Drag & Drop**, que permiten modificar el estado de una tarea en tiempo real sin recargar la página.

El **backend** procesa estas actualizaciones a través de la vista kanban_board(request) y la ruta /tarea/&lt;id&gt;/cambiar-estado/, que recibe solicitudes AJAX y actualiza el campo estado del modelo Tarea. Esto garantiza sincronización inmediata entre la base de datos y la interfaz.

El diseño se apoya en colores diferenciales: #EDE9FE (pendiente), #DDD6FE (en progreso), #D1FAE5 (completada) y #FECACA (bloqueada), reforzando la claridad visual y la comprensión del flujo de trabajo.

**3.2 Backlog Lista - Control visual de tareas**

El **Backlog Lista** actúa como panel de control global de todas las tareas. En el frontend, se renderiza una colección de tarjetas (. tarea-card) con bordes redondeados, fondo degradado y un sombreado ligero que las hace destacar sobre el fondo "niebla lila". Los usuarios pueden filtrar por integrante, sprint o estado mediante menús desplegables &lt;select&gt; que disparan la actualización automática de la página usando onchange="this. form.submit()".

En el **backend**, la vista backlog_lista(request) aplica los filtros seleccionados, consulta los modelos Tarea, Epica y Sprint, y retorna el conjunto de resultados. También gestiona permisos, controlando qué acciones (crear, eliminar, cerrar) están disponibles según el rol del usuario autenticado.

Los botones de acción utilizan las clases .btn-primary, .btn-danger y .btn-secondary, personalizadas con sombras (box-shadow: 0 8px 22px rgba(109,40,217,.18)) y efectos de brillo al pasar el cursor (filter: brightness(1.06);).

**3.3 Daily Resumen - Registro de reportes diarios**

El **Daily Resumen** permite al equipo revisar el progreso diario de los integrantes. Cada registro muestra qué hizo el usuario el día anterior, qué planea hacer hoy y si enfrenta impedimentos. Los estados visuales se distinguen mediante los estilos .estado-ok { color: #28A745; } para reportes en horario y .estado-fuera { color: #D62F52; } para entregas tardías.

En el **frontend**, la tabla se estructura con &lt;th&gt; y &lt;td&gt; cuidadosamente alineados, con espacios amplios y tipografía legible. En el **backend**, la vista daily_resumen(request) filtra los registros según permisos y roles, asegurando que cada usuario solo acceda a la información correspondiente.

**4) Componentes del frontend y herramientas de estilo**

El frontend combina consistencia visual con adaptabilidad funcional. Los componentes principales incluyen:

- **Botones y acciones rápidas:** cada botón es una combinación entre Bootstrap y personalización NEUSI. Por ejemplo, los botones de confirmación usan morado (#6D28D9) y los de cancelación gris (#6C757D), todos con sombras y transiciones suaves.
- **Tablas y tarjetas:** emplean esquinas redondeadas, sombras ligeras y bordes claros, garantizando contraste suficiente sobre el fondo.
- **Formularios:** usan validaciones nativas HTML5 (required, type="file") y estilos visuales que destacan campos activos mediante box-shadow: 0 0 0 4px rgba(109,40,217,.18);.
- **Alertas y modales:** implementados con Bootstrap 5, pero adaptados al esquema NEUSI mediante gradientes y bordes con opacidad controlada.

**5) Funciones JavaScript destacadas**

El JavaScript en NEUSI se mantiene ligero, nativo y orientado a funciones específicas, sin dependencias adicionales. Sus principales propósitos son:

- **Gestión de eventos drag & drop** en Kanban, sincronizando en tiempo real los estados de las tareas.
- **Confirmaciones visuales y modales**, garantizando que el usuario confirme acciones críticas antes de ejecutarlas.
- **Autofiltros dinámicos** que permiten actualizar resultados de manera inmediata sin requerir botones extra.
- **Validaciones previas** a la carga de archivos en formularios, mejorando la robustez del sistema.