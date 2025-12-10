#  Subcontractor App - Sistema de Gestión de Obras Inteligente

Plataforma integral para el control de asistencia, gestión financiera y seguridad operativa en proyectos de construcción. Diseñado para detectar fraudes de asistencia y prevenir quiebras mediante proyección de gastos.

##  Características Principales

###  Seguridad Anti-Fraude (Nivel Bancario)
* **Device Binding:** Vinculación única de dispositivo. Si un trabajador intenta marcar desde otro celular, el sistema lo bloquea.
* **Algoritmo de "Viajes Imposibles":** El backend calcula la velocidad de desplazamiento entre dos marcas. Si es físicamente imposible (teletransportación), rechaza la asistencia.
* **Validación Biométrica:** Uso forzado de cámara en vivo (Selfie) bloqueando la carga de archivos de galería.
* **Auditoría de Red:** Registro de IP y Trazabilidad de modificaciones por parte de Jefes de Obra.

### Inteligencia de Negocios (BI)
* **Proyección de Quiebra:** Algoritmo que predice si la obra será rentable o no basándose en el "Burn Rate" (velocidad de gasto) actual.
* **Control de Multas:** Cálculo automático de impacto financiero por retrasos contractuales (valor UF/Día).
* **Reportes PDF:** Generación nativa de informes ejecutivos para gerencia.

### Interfaz Móvil (PWA Ready)
* Diseño **Mobile-First** con Bootstrap 5.
* API REST integrada (`/v1/api/`) lista para conexión con App Nativa (Android/iOS).

## Tecnologías Utilizadas
* **Backend:** Django 5.2, Python 3.13
* **API:** Django REST Framework
* **Base de Datos:** PostgreSQL (Supabase)
* **Frontend:** Bootstrap 5, Jinja2
* **Reportes:** ReportLab (PDF), Chart.js (Gráficos)
* **Infraestructura:** Render, WhiteNoise


