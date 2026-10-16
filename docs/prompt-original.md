# Prompt original del proyecto

Recibido el 15 de octubre de 2026. Texto del usuario conservado con ajustes de formato para facilitar su lectura.

Quiero iniciar un nuevo proyecto de agente de IA, pero necesito que la estructura general del proyecto sea similar a la que utilizamos previamente en SpendWiseAI.

IMPORTANTE: No quiero copiar SpendWiseAI funcionalmente, porque este proyecto resuelve un problema distinto. Lo que quiero reutilizar es el enfoque de arquitectura, organización del repositorio, separación de responsabilidades, modularidad, configuración y metodología de desarrollo que usamos en SpendWiseAI.

Si tienes acceso al proyecto/repositorio anterior de SpendWiseAI, revísalo primero y úsalo como referencia arquitectónica.

## Objetivo del nuevo proyecto

Construir un agente de IA capaz de detectar automáticamente compromisos o pendientes que nacen dentro de conversaciones, correos, reuniones o textos, identificar qué se debe hacer, quién es el responsable y para cuándo debe realizarse, y permitir hacer seguimiento hasta su cierre.

Ejemplos:

- “Te envío la propuesta mañana.”
- “Te confirmo el viernes.”
- “Queda pendiente revisar el contrato.”
- “Agéndame el sábado a las 4.”
- “Te pago el 15.”
- “Avísame cuando llegue el producto.”

El agente debe convertir este tipo de lenguaje natural en compromisos estructurados.

Ejemplo de salida:

```json
{
  "title": "Enviar propuesta actualizada",
  "responsible": "Jaime",
  "due_date": "2026-10-16",
  "due_time": "15:00",
  "priority": "medium",
  "status": "pending",
  "confidence": 0.95,
  "missing_information": []
}
```

También debe identificar compromisos incompletos.

Ejemplo: “Tenemos que revisar el contrato.”

Salida esperada:

```json
{
  "title": "Revisar contrato",
  "responsible": null,
  "due_date": null,
  "status": "incomplete",
  "missing_information": [
    "responsible",
    "due_date"
  ]
}
```

## ALCANCE DEL MVP

El MVP debe permitir:

1. Ingresar o pegar una conversación/texto.
2. Analizarla mediante un LLM.
3. Detectar uno o varios compromisos.
4. Extraer:
   - título de la tarea
   - descripción
   - responsable
   - contraparte
   - fecha límite
   - hora límite
   - prioridad
   - contexto/origen
   - nivel de confianza
   - información faltante
5. Mostrar los compromisos detectados antes de guardarlos.
6. Permitir al usuario:
   - editar
   - aceptar
   - descartar
7. Guardar los compromisos aprobados.
8. Mostrar un dashboard de compromisos.
9. Clasificarlos como:
   - pending
   - incomplete
   - overdue
   - completed
   - discarded
10. Permitir cambiar manualmente su estado.
11. Dejar preparada la arquitectura para incorporar después:
    - recordatorios automáticos
    - Gmail
    - Google Calendar
    - WhatsApp
    - reuniones/transcripciones
    - múltiples usuarios

## REFERENCIA DE SPENDWISEAI

Quiero que tomes SpendWiseAI como referencia especialmente en los siguientes aspectos:

- estructura clara de carpetas
- separación entre frontend y backend
- configuración mediante variables de entorno
- código modular
- separación entre lógica de negocio y lógica de IA
- uso de servicios independientes
- modelos/esquemas claramente definidos
- endpoints REST organizados
- manejo centralizado de configuración
- manejo de errores
- logging
- pruebas
- documentación del proyecto
- facilidad para ejecutar el proyecto localmente
- Docker/Docker Compose si aplica
- README claro con pasos de instalación y ejecución

Si SpendWiseAI utilizaba patrones o componentes reutilizables que tengan sentido en este nuevo proyecto, propón reutilizarlos.

Sin embargo: NO copies módulos específicos de finanzas, categorías, presupuestos o lógica propia de SpendWiseAI. Adapta únicamente los patrones arquitectónicos y de organización útiles.
