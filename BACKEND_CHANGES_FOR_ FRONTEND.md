# Notas para Frontend: Ajustes Requeridos por Refactorización del Backend

Este documento resume los cambios realizados en la API del backend que afectan la forma en que el frontend debe interactuar con ella.

## 1. Autenticación (`/api/v1/auth`, `/api/v1/users`)

*   **Manejo de Errores Mejorado:**
    *   `/api/v1/auth/token` (Login): Ahora devuelve errores HTTP más específicos:
        *   `401 Unauthorized` (`InvalidCredentialsError`): Para email/contraseña incorrectos.
        *   `403 Forbidden` (`UserInactiveError`): Si el usuario está inactivo.
        *   `500 Internal Server Error`: Para errores inesperados.
    *   `/api/v1/auth/register`: Ahora devuelve `409 Conflict` (`EmailAlreadyExistsError`) si el email ya existe.
    *   `/api/v1/auth/refresh`: Ahora devuelve errores HTTP más específicos:
        *   `401 Unauthorized` (`InvalidTokenError`): Si el token no es válido.
        *   `403 Forbidden` (`UserInactiveError`): Si el usuario asociado al token está inactivo.
        *   `410 Gone` (`TokenExpiredError`): Si el token ha expirado.
        *   `404 Not Found` (`UserNotFoundError`): Si el usuario del token no se encuentra.
        *   `500 Internal Server Error`: Para otros errores inesperados durante el refresco.
    *   **Acción Frontend:** Revisar el manejo de errores para estas rutas y ajustarlo a los nuevos códigos de estado y posibles mensajes de detalle.
*   **Respuestas de Usuario:**
    *   Los endpoints que devuelven información del usuario (ej. `/api/v1/users/me`, registro, actualización) ahora devuelven objetos serializados por Pydantic según el schema `UserResponse`.
    *   **Acción Frontend:** Verificar que el frontend espera la estructura definida en `UserResponse` y la maneja correctamente. El campo `role` podría estar incluido ahora (verificar schema `UserResponse`).

## 2. Documentos (`/api/v1/documents`)

*   **¡CAMBIO DE RUTA PRINCIPAL!**
    *   La ruta base para los endpoints de documentos ha cambiado de `/api/v1/document` a `/api/v1/documents`.
    *   **Acción Frontend:** **Actualizar todas las llamadas a la API** que usaban `/api/v1/document/...` para usar `/api/v1/documents/...`.
*   **`POST /api/v1/documents/process-embeddings/{id}` (Procesamiento de Documentos):**
    *   Este endpoint **ahora es asíncrono**. En lugar de esperar a que el procesamiento se complete, devuelve inmediatamente un `HTTP 202 Accepted`.
    *   La respuesta indica que el procesamiento ha sido *programado* en segundo plano.
    *   Formato de respuesta (`202 Accepted`):
        ```json
        {
          "status": "processing_scheduled",
          "message": "Embedding processing scheduled for document {document_id}.",
          "document_id": "{document_id}"
        }
        ```
    *   **Acción Frontend:** 
        *   Actualizar la lógica para manejar la respuesta `202 Accepted`.
        *   No esperar la finalización del procesamiento en la respuesta directa.
        *   Implementar un mecanismo para verificar el estado del documento periódicamente (ej. haciendo polling a `GET /api/v1/documents/{id}`) o usar WebSockets (si están disponibles) para saber cuándo se completa el procesamiento y los embeddings están listos para ser usados (ej. para búsquedas).
*   **`POST /api/v1/documents/embeddings/{id}`:**
    *   El cuerpo de la solicitud (`payload`) **debe** ajustarse al schema `EmbeddingsPayload`.
    *   Formato esperado: `{"embeddings": [[...], ...], "chunks_text": ["...", ...], "model": "..."}`.
    *   **Acción Frontend:** Asegurar que el payload enviado cumpla estrictamente con este schema.
*   **`POST /api/v1/documents/search`:**
    *   El cuerpo de la solicitud (`search_params`) **debe** ajustarse al schema `SearchRequest`.
    *   Formato esperado: `{"query": "...", "model": "...", "limit": 5, "min_similarity": 0.5, "document_id": null | "uuid-string"}`. Se aplican valores predeterminados y validaciones de rango para `limit` y `min_similarity`.
    *   **Acción Frontend:** Asegurar que el payload enviado cumpla estrictamente con este schema.
*   **`GET /api/v1/documents/{id}`:**
    *   La respuesta ahora se genera directamente serializando el objeto `Document` del backend usando el schema `DocumentResponse`.
    *   El campo `processing_results` en la respuesta puede contener resultados "sintetizados" (creados a partir de la última ejecución de pipeline) que **no tendrán un `id`**.
    *   **Acción Frontend:** Asegurar que el manejo de la respuesta `DocumentResponse` es correcto y que puede manejar elementos en `processing_results` que tengan `id: null` o `undefined`.

## 3. Pipelines (`/api/v1/pipelines`, `/api/v1/executions`)

*   **Rutas de Configuración (`/api/v1/configs/...`)**
    *   Los endpoints para gestionar *configuraciones* de pipelines **permanecen bajo `/api/v1/configs/...`** (Ej: `POST /configs`, `GET /configs/{id}`, etc.).
    *   **Acción Frontend:** Verificar que las llamadas a la API para gestión de configuraciones usan la ruta `/configs/`.
*   **Respuestas de Configuración (`/api/v1/configs/*`)**
    *   Las respuestas para obtener configuraciones (individuales o listas) ahora se serializan directamente desde el objeto `Pipeline` del backend usando el schema `PipelineConfigResponse`. El formato debería ser consistente, pero depende de la definición exacta del schema.
    *   **Acción Frontend:** Verificar que el manejo de la respuesta `PipelineConfigResponse` es correcto.
*   **Rutas de Ejecución (`/api/v1/executions/...`)**
    *   Los endpoints para gestionar *ejecuciones* de pipelines están bajo `/api/v1/executions/...` (Ej: `POST /executions`, `GET /executions/{id}`).
*   **`GET /api/v1/executions/{id}` y otras respuestas de ejecución:**
    *   Las respuestas ahora se generan directamente serializando el objeto `PipelineExecution` del backend usando el schema `PipelineExecutionResponse`. Se eliminó la construcción manual de un diccionario.
    *   El schema `PipelineExecutionResponse` fue ajustado (se eliminó `result` duplicado, se usa `error_message`). Debería incluir `pipeline_name`.
    *   **Acción Frontend:** Asegurar que el manejo de la respuesta `PipelineExecutionResponse` es correcto, basándose en la estructura definida en el schema (incluyendo `pipeline_name`, `error_message`, etc.).

## General

*   **Manejo de Errores:** En general, esperar potencialmente más códigos de estado HTTP específicos (4xx) en lugar de solo errores 500 genéricos, ya que se ha mejorado el manejo de excepciones personalizadas.

**Recomendación:**

Probar exhaustivamente las interacciones del frontend con estos endpoints modificados. Usar las herramientas de desarrollo del navegador (pestaña Network) para inspeccionar las solicitudes y respuestas si surgen problemas.