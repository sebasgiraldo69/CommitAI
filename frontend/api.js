export class ApiError extends Error {
  constructor(message, status = 0, details = []) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

export async function request(
  path,
  { method = "GET", body, headers = {}, timeout = 90000 } = {},
) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(path, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });

    let data;

    try {
      data = await response.json();
    } catch {
      throw new ApiError(
        "El servidor devolvió una respuesta que no se pudo interpretar.",
        response.status,
      );
    }

    if (!response.ok) {
      throw new ApiError(
        data.error?.message || "No se pudo completar la solicitud.",
        response.status,
        data.error?.details || [],
      );
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    if (error.name === "AbortError") {
      throw new ApiError(
        "Se agotó el tiempo de espera. Puedes reintentar.",
      );
    }

    throw new ApiError(
      "No se pudo conectar con el servidor. Revisa que esté ejecutándose.",
    );
  } finally {
    clearTimeout(timer);
  }
}