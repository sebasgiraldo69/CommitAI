# Plan de implementación de CommitAI

Fecha: 2026-10-15. Estado: fase 0 completada; fases 1–7 pendientes.

## Resultado esperado

Entregar un MVP local que permita pegar texto, extraer compromisos mediante un LLM, revisarlos, guardar únicamente los aceptados y darles seguimiento en un dashboard. La referencia arquitectónica es SpendWiseAI, revisado en `../Proyecto`; sus funcionalidades financieras quedan fuera de este proyecto.

El desarrollo avanza por entregas verificables. Cada fase termina con una demostración y el cumplimiento de sus criterios de aceptación. Las pruebas se incorporan en la fase que introduce el comportamiento, no se dejan todas para el final.

## Base técnica propuesta

- Backend: Python, FastAPI y Pydantic, con rutas, servicios, dominio, repositorios y proveedor de IA separados.
- Frontend: HTML, CSS y JavaScript modular para mantener la sencillez del proyecto de referencia. Si se elige otro framework, registrarlo antes de iniciar la interfaz.
- Persistencia: SQLite para el MVP local, con migraciones versionadas y acceso mediante repositorios.
- IA: adaptador intercambiable que devuelva datos estructurados; proveedor y modelo configurables. Seleccionar el proveedor y comprobar su contrato vigente durante la fase de integración.
- Configuración: variables de entorno, `.env.example` sin secretos y un módulo central de configuración.
- Ejecución: un proceso de backend para la primera entrega; frontend separado en carpetas, que puede servirse desde el mismo origen. Docker es un entregable opcional de empaquetado.

Estos valores son una propuesta de trabajo, no requisitos adicionales del usuario. “Servicios independientes” se interpreta inicialmente como módulos con responsabilidades separadas dentro de una aplicación, sin necesidad de desplegar microservicios.

## Vista general

| Fase | Resultado demostrable | Dependencia |
| --- | --- | --- |
| 0. Reglas y contratos | Ejemplos y reglas de negocio definidos | Documentos actuales |
| 1. Base del proyecto | Aplicación arranca y responde a una comprobación de salud | 0 |
| 2. Dominio y persistencia | Compromisos se guardan y actualizan mediante API | 1 |
| 3. Extracción con IA | Texto produce candidatos validados sin guardarlos | 2 |
| 4. Revisión del usuario | Texto → edición → aceptación → guardado | 3 |
| 5. Dashboard y seguimiento | Consulta, filtros, edición y estados funcionando | 4 |
| 6. Validación y entrega | MVP reproducible y evaluado | 5 |
| 7. Evolución | Integraciones y usuarios incorporados por entregas | MVP validado |

## Fase 0 — Definir reglas y contratos

**Objetivo:** evitar que el modelo de IA o la interfaz determinen accidentalmente las reglas del producto.

Tareas:

- [x] Definir los esquemas de entrada, candidato extraído y compromiso persistido. Incluir todos los campos del prompt, identificadores, marcas de tiempo, zona horaria y cita de origen.
- [x] Diferenciar responsable y contraparte; aceptar participantes y hablante como contexto opcional.
- [x] Definir fecha de referencia de la conversación y zona horaria configurable, inicialmente `America/Bogota`.
- [x] Documentar reglas para fechas relativas, horas ambiguas, tareas sin fecha y condiciones como “cuando llegue el producto”.
- [x] Definir la tabla de estados y transiciones, incluida su relación con la edición manual.
- [x] Preparar un conjunto inicial de al menos 30 textos etiquetados: ejemplos del prompt, textos sin tareas, varios compromisos, negaciones, responsables implícitos y fechas ambiguas.
- [x] Registrar decisiones en `docs/reglas-negocio.md` y contratos en `docs/contratos-api.md`.

Reglas iniciales aceptadas y desarrolladas en [reglas de negocio](reglas-negocio.md). Los [contratos](contratos-api.md) y los [30 casos etiquetados](../evals/casos-fase-0.json) completan la fase documental; no implican pruebas del LLM ejecutadas.

| Tema | Propuesta |
| --- | --- |
| Información desconocida | Usar `null` y señalar faltantes; no inventar datos |
| Título | Obligatorio para guardar; si falta, la revisión debe corregirlo |
| Completitud | Responsable y fecha requeridos para una tarea ordinaria; hora opcional |
| Condiciones | Conservar condición explícita; si no hay fecha, mantener `incomplete` en el MVP y permitir guardado consciente |
| Prioridad | `low`, `medium`, `high`; `medium` como valor por defecto visible y editable |
| Sin hora | Vence al terminar el día local indicado; no mostrar una hora inventada |
| Precedencia automática | `completed`/`discarded` conservan su estado; después `incomplete`, después `overdue`, después `pending` |
| Cambio manual | Completar, descartar y reabrir directamente; solicitar `pending`, `incomplete` u `overdue` exige que los datos cumplan sus reglas, con error claro si no coinciden |
| Descarte en revisión | No crea un compromiso persistido |
| Descarte posterior | Un compromiso guardado puede pasar a `discarded` |
| Texto original | Guardar cita y metadatos necesarios; no guardar toda la conversación por defecto |

**Entregables:** reglas, contratos, casos etiquetados y decisiones técnicas iniciales.

**Criterio de cierre:** cada ejemplo del usuario tiene una salida esperada o una ambigüedad explícita; los cinco estados tienen reglas coherentes. “Te envío la propuesta mañana” no produce un nombre ni una hora sin contexto que los justifique.

## Fase 1 — Preparar la base del proyecto

**Objetivo:** contar con una estructura ejecutable y mantenible.

Tareas:

- [ ] Crear `backend/app/{api/routes,core,schemas,domain,services,ai,repositories,db}`, `backend/tests`, `frontend` y `evals`, siguiendo el análisis inicial.
- [ ] Definir dependencias y versión de Python soportada; documentar instalación en PowerShell.
- [ ] Crear la aplicación, el endpoint `GET /api/health` y la configuración central.
- [ ] Configurar ruta de base de datos, proveedor/modelo, tiempos de espera y zona horaria mediante entorno.
- [ ] Añadir `.gitignore`, `.env.example`, manejo común de errores e identificador de solicitud para logging.
- [ ] Establecer comandos de ejecución, pruebas y revisión estática, y documentarlos en el README.

**Entregables:** estructura base, servidor ejecutable y configuración de desarrollo.

**Criterio de cierre:** desde un entorno nuevo se puede instalar y arrancar siguiendo el README; `/api/health` responde; la aplicación puede arrancar sin clave de IA y explica que el análisis no está configurado cuando se solicita.

## Fase 2 — Implementar dominio, persistencia y API

**Objetivo:** gestionar compromisos sin depender de llamadas al LLM.

Tareas:

- [ ] Implementar esquemas y reglas de completitud, prioridad, fechas y estados definidos en fase 0.
- [ ] Crear la migración inicial y repositorio SQLite con operaciones transaccionales.
- [ ] Implementar servicio de creación por lote de compromisos aceptados; validar todo el lote antes de confirmar su escritura.
- [ ] Evitar duplicados por doble clic o reintento mediante una clave de idempotencia persistida. No confundir esto con deduplicar tareas parecidas semánticamente.
- [ ] Implementar `POST /api/commitments`, `GET /api/commitments`, `GET /api/commitments/{id}` y `PATCH /api/commitments/{id}`.
- [ ] Añadir filtros por estado y responsable, orden por vencimiento y paginación.
- [ ] Calcular el estado efectivo al consultar usando un reloj inyectable. No depender de un proceso programado para mostrar `overdue`.
- [ ] Conservar información de revisión: cita original, valores aprobados y fechas de creación/actualización.

**Verificación:** pruebas de límites temporales, transiciones, datos incompletos, transacciones, idempotencia y errores de validación usando una base temporal.

**Entregables:** API de compromisos operativa y datos persistentes.

**Criterio de cierre:** se puede crear, consultar, editar, completar, descartar y reabrir un compromiso desde la API; los datos sobreviven a un reinicio; un reintento de creación no duplica registros. Un compromiso completado no aparece vencido.

## Fase 3 — Implementar extracción con IA

**Objetivo:** obtener candidatos estructurados y verificables a partir de texto.

Tareas:

- [ ] Implementar la interfaz del proveedor y un adaptador real; mantener prompts y reglas del dominio fuera del transporte HTTP.
- [ ] Crear un proveedor simulado exclusivo para pruebas, con respuestas controladas.
- [ ] Diseñar el prompt y esquema de salida para cero, uno o varios compromisos, incluyendo información faltante, confianza y cita de origen.
- [ ] Implementar `POST /api/analyses` con texto, fecha de referencia, zona horaria y participantes opcionales.
- [ ] Validar tipos, rangos, campos, citas y coherencia temporal después de la respuesta del LLM; recalcular en backend las reglas deterministas.
- [ ] Establecer límites de entrada y tiempos de espera. Tratar el texto analizado como datos, incluso cuando contenga instrucciones dirigidas al agente.
- [ ] Manejar clave ausente, cuota, timeout, rechazo y salida inválida con errores comprensibles. Evitar reintentos ocultos y resultados simulados en el flujo real.
- [ ] Ejecutar los casos etiquetados y registrar proveedor, modelo, versión de prompt y resultados.

**Verificación:** pruebas de contratos y errores con proveedor simulado; evaluación semántica separada con proveedor real cuando haya credenciales configuradas. La simulación no certifica la calidad del LLM.

**Entregables:** análisis de texto por API y reporte inicial de extracción.

**Criterio de cierre:** los ejemplos producen candidatos revisables, los textos sin compromisos devuelven una lista vacía y el análisis nunca crea compromisos persistidos. Si falta acceso al proveedor real, se registra esa validación como pendiente, no como aprobada.

## Fase 4 — Construir ingreso y revisión

**Objetivo:** completar el primer recorrido de usuario de extremo a extremo.

Tareas:

- [ ] Crear pantalla de entrada de texto con fecha de referencia, zona horaria y contexto opcional de participantes.
- [ ] Mostrar estado de análisis y errores conservando el texto ingresado.
- [ ] Mostrar candidatos con sus campos, cita de origen, confianza e información faltante.
- [ ] Permitir editar, aceptar y descartar cada candidato, además de confirmar el guardado de los aceptados.
- [ ] Revalidar en backend las ediciones y mostrar errores junto al campo correspondiente.
- [ ] Permitir guardar candidatos incompletos con su estado claramente visible.
- [ ] Evitar doble envío; descartar respuestas antiguas si el usuario inicia otro análisis.
- [ ] Mostrar confirmación de guardado y manejar el caso de cero candidatos.

**Verificación:** recorrido de navegador con varios candidatos: editar uno, aceptar dos y descartar otro; comprobar que únicamente los aceptados existen en la base. Repetir un caso con error de red y reintento.

**Entregables:** flujo usable de texto → revisión → compromisos guardados.

**Criterio de cierre:** el usuario realiza el recorrido completo desde la interfaz y ninguna extracción se guarda sin aceptación.

## Fase 5 — Construir dashboard y seguimiento

**Objetivo:** permitir gestionar los compromisos después de aceptarlos.

Tareas:

- [ ] Mostrar compromisos y contadores de `pending`, `incomplete`, `overdue`, `completed` y `discarded`.
- [ ] Añadir filtros por estado y responsable, orden por fecha y paginación coherente con la API.
- [ ] Añadir vista de detalle con contexto y faltantes, edición de campos y controles de estado.
- [ ] Permitir completar, descartar y reabrir; explicar cómo corregir campos para otros cambios de estado.
- [ ] Actualizar los estados al cargar y refrescar el dashboard; definir un refresco periódico mientras esté abierto para reflejar nuevos vencimientos.
- [ ] Resolver estados vacíos, errores, uso con teclado y visualización en móvil.

**Verificación:** escenarios con reloj controlado para vencimiento, tarea sin hora y cambio de fecha; completar los datos de un compromiso incompleto y verificar reclasificación; comprobar que filtros, contadores y listado coinciden.

**Entregables:** dashboard y seguimiento manual completo.

**Criterio de cierre:** se puede seguir un compromiso desde su aceptación hasta su cierre, corregirlo y reabrirlo sin perder datos ni mostrar estados contradictorios.

## Fase 6 — Validar y preparar la entrega del MVP

**Objetivo:** entregar una aplicación reproducible, con límites conocidos y evidencia de funcionamiento.

Tareas:

- [ ] Ejecutar las pruebas de dominio, repositorios, API y recorridos principales; corregir fallos antes de ampliar el alcance.
- [ ] Evaluar el conjunto etiquetado con el proveedor real y registrar aciertos, omisiones, falsos positivos e invenciones de responsables/fechas.
- [ ] Medir precisión y cobertura de detección, exactitud de campos cuando son conocidos y reconocimiento de información faltante. Reportar tanto porcentajes como número de casos.
- [ ] Como metas iniciales propuestas: precisión y cobertura de detección de al menos 90 % en el conjunto de evaluación, y cero responsables/fechas inventados en los casos críticos definidos. Estas metas se fijan antes de ajustar el prompt y no implican garantías fuera del conjunto evaluado.
- [ ] Separar casos de ajuste y de evaluación final para reducir el sesgo de medir solo ejemplos usados para mejorar el prompt.
- [ ] Comprobar límites de entrada, errores del proveedor y ausencia de claves o conversaciones completas en logs.
- [ ] Revisar instalación desde cero y documentar configuración, ejecución, pruebas, arquitectura, limitaciones y solución de errores habituales.
- [ ] Documentar copia/restauración de SQLite y comportamiento de las migraciones.
- [ ] Si aporta valor a la entrega, añadir Docker y Compose con volumen persistente y configuración externa; verificar que recrear el contenedor conserva los datos.
- [ ] Preparar un guion de demostración con casos completos, incompletos, ambiguos y vencidos.

**Entregables:** README reproducible, reporte de pruebas, reporte de evaluación y guion de demostración; contenedor opcional.

**Criterio de cierre:** se cumplen los criterios del prompt original, los casos críticos pasan, la validación real está documentada y otra persona puede ejecutar el MVP siguiendo el README. Los fallos conocidos y las limitaciones se declaran expresamente.

## Fase 7 — Evolución posterior al MVP

Cada integración se planifica como una entrega independiente después de validar el uso del MVP.

| Entrega | Preparación necesaria | Criterio mínimo |
| --- | --- | --- |
| Recordatorios | Programador, registro de envíos, política horaria y canal elegido | No duplicar avisos ni enviar por compromisos cerrados |
| Múltiples usuarios | Autenticación, propiedad de registros y aislamiento en todas las consultas | Un usuario no puede leer ni modificar datos de otro |
| Gmail | Autorización de cuenta, selección de mensajes y deduplicación por origen | Importar texto con trazabilidad y mantener revisión previa |
| Google Calendar | Vinculación de cuenta, zona horaria y asociación tarea/evento | Crear o modificar eventos solo por una acción autorizada y evitar duplicados |
| Reuniones/transcripciones | Ingesta, hablantes y marcas temporales | Mantener referencia al fragmento y hablante original |
| WhatsApp | Definir mecanismo de integración permitido y credenciales | Ingesta trazable reutilizando los mismos casos de uso |

Las integraciones personales en una aplicación compartida dependen primero del aislamiento entre usuarios. La detección automática de eventos condicionales se estudia en esta etapa; el MVP solo conserva su condición textual.

## Cómo trabajar fase por fase

1. Al comenzar una fase, revisar sus dependencias y convertir sus tareas en una lista de trabajo concreta.
2. Implementar cambios pequeños y mantener los documentos alineados con el código real.
3. Ejecutar las verificaciones de la fase y registrar resultados, limitaciones y pendientes.
4. Marcar la fase como completada solo cuando cumple sus criterios de cierre; dejar un commit identificable cuando se configure el repositorio Git.
5. Continuar con la fase siguiente sin incorporar integraciones que amplíen el alcance del MVP.

No se asignan fechas de calendario porque todavía no hay disponibilidad de equipo ni fecha de entrega definida. El orden y los criterios permiten convertir el plan en un cronograma cuando se conozcan esas restricciones.

## Seguimiento

- [x] Fase 0: reglas y contratos.
- [ ] Fase 1: base del proyecto.
- [ ] Fase 2: dominio, persistencia y API.
- [ ] Fase 3: extracción con IA.
- [ ] Fase 4: ingreso y revisión.
- [ ] Fase 5: dashboard y seguimiento.
- [ ] Fase 6: validación y entrega del MVP.
- [ ] Fase 7: evolución posterior, fuera del alcance del MVP.
