# UX/UI Quality Evaluation

## Objetivo

Evaluar la experiencia de usuario de CommitAI durante el flujo crítico de detección, revisión, guardado y seguimiento de compromisos.

Se observaron los siguientes estados:

- loading;
- empty;
- error;
- success;
- recuperación;
- accesibilidad básica;
- confianza;
- consistencia de interacción.

---

## Loading

### Observación
Durante el análisis, el sistema muestra un estado de procesamiento y deshabilita acciones que podrían generar solicitudes repetidas.

### Resultado
Correcto.

El usuario recibe retroalimentación visual mientras espera el análisis.

---

## Empty state

### Observación
Cuando no se detectan compromisos, el sistema muestra:

> “No se detectaron compromisos en este texto”.

### Resultado
Correcto.

El mensaje es claro y permite al usuario mantener o modificar la conversación.

---

## Error state

### Observación
Las entradas vacías y aquellas formadas únicamente por espacios reciben validación.

### Resultado
Correcto en casos simples.

### Oportunidad de mejora
Cuando la entrada supera o se aproxima al límite de 20.000 caracteres, el sistema no explica suficientemente el motivo por el cual el análisis no puede continuar.

---

## Success state

### Observación
Cuando se detectan compromisos correctamente, el usuario puede:

- revisarlos;
- seleccionarlos;
- editarlos;
- guardarlos;
- visualizarlos;
- marcarlos como completados.

### Resultado
Correcto.

---

## Recuperación

### Hallazgo inicial
Se detectó una falla importante:

después de realizar un análisis, si el usuario modificaba la conversación, los candidatos anteriores permanecían visibles y podían guardarse.

### Riesgo UX
El usuario podía interpretar que los resultados seguían siendo válidos aunque ya no correspondieran al texto visible.

Esto afectaba:
- confianza;
- consistencia;
- integridad de datos;
- comprensión del estado de la interfaz.

### Corrección aplicada
Al modificar la conversación:

- se eliminan resultados anteriores;
- se limpian selecciones;
- se deshabilita el guardado;
- se solicita un nuevo análisis;
- se muestra el mensaje:

> “El texto cambió. Analiza nuevamente para detectar compromisos”.

### Resultado después de la corrección
Correcto.

La interfaz refleja de forma coherente el estado actual del texto y evita utilizar resultados obsoletos.

---

## Prompt Injection y confianza

### Observación
Durante la prueba adversarial, una instrucción maliciosa incluida dentro del contenido de la conversación no modificó el comportamiento esperado del agente.

### Resultado
Correcto para el caso evaluado.

El compromiso legítimo fue extraído y no se realizaron acciones automáticas sin confirmación del usuario.

---

## Accesibilidad básica

### Observaciones
La interfaz utiliza:
- mensajes visibles de estado;
- botones deshabilitados cuando una acción no está disponible;
- revisión explícita antes de guardar;
- separación visual entre análisis y compromisos.

### Estado
Aceptable para el MVP.

### Deuda pendiente
Realizar posteriormente una revisión más profunda de:
- navegación por teclado;
- contraste;
- labels;
- mensajes accesibles para lectores de pantalla.

---

## Hallazgo prioritario

La principal falla UX detectada fue la persistencia de candidatos después de modificar el texto analizado.

El problema fue priorizado porque podía provocar acciones incorrectas, no únicamente confusión visual.

---

## Medición antes y después

### Antes
- resultados obsoletos visibles;
- selecciones antiguas activas;
- guardado disponible;
- usuario sin advertencia.

### Después
- resultados anteriores eliminados;
- selecciones limpiadas;
- guardado bloqueado;
- nuevo análisis requerido;
- mensaje explícito para el usuario.

---

## Próxima mejora

Agregar un contador visible de caracteres y feedback explícito al aproximarse al límite máximo permitido.