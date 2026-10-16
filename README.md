# CommitAI

Aplicación local que transforma conversaciones en compromisos estructurados,
permite revisarlos antes de guardarlos y facilita su seguimiento.

## Funcionalidades

- Analizar texto mediante un LLM.
- Detectar uno o varios compromisos.
- Extraer responsable, contraparte, fecha, hora, prioridad y contexto.
- Señalar información faltante y ambigüedades.
- Editar candidatos y seleccionar cuáles guardar.
- Consultar compromisos en un dashboard.
- Filtrar por estado y responsable.
- Completar, descartar, editar y reabrir compromisos.
- Conservar los registros en SQLite.

Estados disponibles: `pending`, `incomplete`, `overdue`, `completed`
y `discarded`.

## Arquitectura

```text
backend/
  app/
    api/routes/       Endpoints REST
    core/             Configuración y errores
    schemas/          Contratos y validación
    domain/           Reglas de estados y vencimiento
    services/         Casos de uso
    ai/               Proveedor y prompts
    repositories/     Persistencia
    db/               Conexiones y migraciones
  tests/              Pruebas automatizadas
frontend/             Interfaz HTML, CSS y JavaScript
evals/                Casos y ejecución de evaluación de IA
docs/                 Requisitos, contratos y documentación
data/                 Base de datos local
```

El backend usa FastAPI y Pydantic. El frontend se sirve desde el mismo
servidor. SQLite almacena los compromisos y las claves de idempotencia
para evitar duplicados al reintentar un guardado.

La arquitectura toma como referencia SpendWiseAI, sin reutilizar su
lógica financiera.

## Requisitos

- Python 3.11 o superior.
- PowerShell para los comandos de esta guía.
- Acceso a la API del proveedor configurado para analizar texto.
- Una clave válida y acceso al modelo seleccionado.

Consultar y editar compromisos guardados no requiere llamar a la IA.

## Instalación

Ejecutar desde la carpeta raíz de CommitAI:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Crear `.env` desde la plantilla únicamente si todavía no existe:

```powershell
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Editar `.env` y configurar:

```dotenv
APP_NAME=CommitAI
LOG_LEVEL=INFO
DATABASE_PATH=data/commitai.db
APP_TIMEZONE=America/Bogota

AI_PROVIDER=openai
AI_MODEL=gpt-4.1-mini
AI_API_KEY=REEMPLAZAR_POR_LA_CLAVE_REAL

AI_CONNECT_TIMEOUT_SECONDS=5
AI_READ_TIMEOUT_SECONDS=35
```

No subir `.env` ni claves al repositorio. Las variables definidas en la
terminal tienen prioridad sobre `.env`.

El modelo indicado es el usado durante el desarrollo. El acceso depende
de la cuenta y configuración del proveedor.

## Ejecución

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --no-access-log
```

Direcciones:

- Análisis y revisión: http://127.0.0.1:8000/
- Dashboard: http://127.0.0.1:8000/dashboard
- Documentación de API: http://127.0.0.1:8000/docs
- Salud del proceso: http://127.0.0.1:8000/api/health

Mantener abierta la terminal. Detener el servidor con Ctrl+C.

La base de datos se crea al iniciar. Las migraciones aplicadas quedan
registradas en `schema_migrations`.

Abrir la interfaz desde FastAPI, no directamente como archivo HTML ni
mediante Live Server. Reiniciar el servidor después de modificar `.env`.

## Uso

1. Pegar una conversación.
2. Indicar su fecha de referencia y zona horaria.
3. Analizar el texto.
4. Revisar y corregir los candidatos.
5. Marcar los compromisos que se desea guardar.
6. Pulsar “Guardar seleccionados”.
7. Consultar y actualizar los registros desde el dashboard.

Los candidatos no seleccionados no se guardan. Un compromiso incompleto
puede guardarse y completarse posteriormente.

Las fechas relativas se interpretan usando la fecha de la conversación.
El vencimiento se determina usando el reloj actual del servidor.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe -m ruff check backend
```

Las pruebas del proveedor usan respuestas simuladas y no consumen API.

Las evaluaciones siguientes sí realizan llamadas reales:

```powershell
.\.venv\Scripts\python.exe -m evals.run_extraction --live --split development
.\.venv\Scripts\python.exe -m evals.run_extraction --live --split evaluation
```

Los reportes se generan en `evals/results/`.

## Evidencia de validación

- 19 pruebas automatizadas aprobadas en la ejecución compartida.
- Ruff aprobado después de ordenar las importaciones.
- Prompt v2: 20 casos de desarrollo revisados sin los errores materiales
  previamente encontrados.
- Prompt v3: 10 casos de regresión revisados con resultados esperados.
- Los 20 casos de desarrollo no se han vuelto a verificar con v3.
- El conjunto denominado `evaluation` se utilizó para ajustar el prompt;
  sus resultados posteriores son de regresión, no una evaluación independiente.
- Se realizó una comprobación independiente visible:
  “Mariana: Le enviaré el diseño a Pedro mañana a las 10:30”.
  Las capturas muestran responsable Mariana, fecha 2026-10-16, hora 10:30,
  guardado y consulta en el dashboard.
- La contraparte aparece en el título de ese caso, pero su campo específico
  no se comprobó en las capturas.
- Por decisión del usuario no se ejecutaron los otros cinco casos nuevos propuestos.

Estos resultados no garantizan exactitud para cualquier conversación.
La revisión humana sigue siendo parte del flujo.

## Limitaciones del MVP

- Aplicación local sin autenticación ni aislamiento entre múltiples usuarios.
- Sin integración automática con Gmail, Calendar o WhatsApp.
- Sin recordatorios automáticos ni detección de cumplimiento de condiciones.
- El modelo puede omitir compromisos o interpretar datos incorrectamente.
- La confianza es una estimación del modelo, no una garantía.
- La conversación se envía al proveedor durante el análisis.
- Los registros guardan fragmentos de origen y datos revisados.
- Los borradores no guardados pueden perderse al recargar la página.
- El guardado pendiente se conserva en la sesión de la pestaña para reintentar.
- Los filtros y la paginación se calculan en memoria; adecuados para el
  volumen inicial, pendientes de optimización para conjuntos grandes.
- Las dependencias están definidas por rangos; no existe todavía un archivo
  de versiones fijadas que garantice reproducir exactamente el entorno.
- Se observó una advertencia de obsolescencia entre TestClient y HTTPX;
  las pruebas terminaron correctamente.
- No se ha certificado una instalación desde cero ni un despliegue de producción.
- No se ha documentado todavía una prueba de recuperación tras fallo de red
  durante el guardado.

## Problemas frecuentes

### El navegador rechaza la conexión

Iniciar el servidor y mantener la terminal abierta.

### Analizar recarga la página

Comprobar que `frontend/api.js` y `frontend/app.js` estén guardados y
contengan el código. Recargar con Ctrl+F5.

### `provider_auth`

Revisar la clave y los permisos del proveedor. Reiniciar el servidor
después de corregir `.env`.

### `provider_quota`

Revisar los límites o la cuota del proyecto de API.

### `provider_timeout`

Reintentar conservando el texto original.

### No aparecen cambios visuales

Guardar los archivos y recargar con Ctrl+F5.

## Documentación

- [Prompt original](docs/prompt-original.md)
- [Análisis inicial](docs/analisis-inicial.md)
- [Plan de implementación](docs/plan-implementacion.md)
- [Reglas de negocio](docs/reglas-negocio.md)
- [Contratos de API](docs/contratos-api.md)
- [Respaldo y recuperación](docs/respaldo-sqlite.md)
- [Guion de demostración](docs/guion-demostracion.md)