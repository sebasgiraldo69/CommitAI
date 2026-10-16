# Guion de demostración de CommitAI

Duración orientativa: 4–5 minutos.

## 1. Problema

“En conversaciones aparecen promesas y pendientes que se pierden entre
mensajes. CommitAI los convierte en registros que podemos revisar y seguir.”

## 2. Analizar una conversación

Abrir http://127.0.0.1:8000/.

Usar como fecha de conversación 2026-10-15 y zona America/Bogota.

Texto:

> Mariana: Le enviaré el diseño a Pedro mañana a las 10:30.

Explicar:

- “Mañana” se interpreta respecto a la fecha de la conversación.
- El responsable es Mariana.
- La fecha esperada es 2026-10-16.
- La hora esperada es 10:30.
- La respuesta debe revisarse porque proviene de un modelo de IA.

El estado dependerá de la fecha actual del servidor. Si la fecha límite
ya pasó, que aparezca vencido es correcto.

## 3. Revisión humana

Mostrar los campos editables.

“La IA propone los datos. La persona puede corregirlos y seleccionar
si desea guardar el compromiso.”

Marcar “Guardar este compromiso” y pulsar “Guardar seleccionados”.

Este paso crea un registro real. Si ya existe uno idéntico de una
demostración anterior, usarlo para el seguimiento o identificar
claramente el nuevo registro.

## 4. Seguimiento

Abrir el dashboard.

- Localizar el compromiso de Mariana.
- Mostrar filtros y contadores.
- Abrir “Ver y editar”.
- Mostrar responsable, contraparte, fecha y cita original.
- Marcarlo como completado y guardar.
- Abrir la pestaña Completados.
- Reabrirlo y explicar que el estado se recalcula.

Si faltan datos, el registro puede conservarse como incompleto.

## 5. Explicación técnica

“El frontend usa HTML, CSS y JavaScript. FastAPI expone la API,
Pydantic valida los datos y SQLite conserva los registros.
El proveedor de IA está separado de las reglas de negocio.”

“Reintentar el mismo guardado utiliza una clave de idempotencia
para evitar crear registros duplicados.”

## 6. Evidencia y límites

- 19 pruebas automatizadas aprobadas.
- Revisión de código con Ruff aprobada.
- Casos de desarrollo y regresión utilizados para mejorar la extracción.
- Una comprobación independiente visible del recorrido de usuario.
- La revisión humana sigue siendo necesaria.
- No hay todavía integraciones automáticas ni múltiples usuarios.

No presentar los casos usados para ajustar el prompt como una evaluación
independiente ni afirmar precisión universal.

## Preparación previa

- Comprobar que el servidor arranque.
- Verificar acceso al proveedor de IA.
- Evitar mostrar `.env` o claves durante la presentación.
- Tener abiertos el análisis y el dashboard.
- Revisar los registros de demostración existentes.
- Conservar capturas de la ejecución previa como evidencia si falla
  la conexión; identificarlas como capturas, no como resultados en vivo.