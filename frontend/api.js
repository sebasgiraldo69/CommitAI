export class ApiError extends Error {
  constructor(message, status = 0, details = []) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

export function getToken() {
  return localStorage.getItem("commitai_token");
}

export function setToken(token) {
  if (token) {
    localStorage.setItem("commitai_token", token);
  } else {
    localStorage.removeItem("commitai_token");
  }
}

export function getUser() {
  const raw = localStorage.getItem("commitai_user");
  try {
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setUser(user) {
  if (user) {
    localStorage.setItem("commitai_user", JSON.stringify(user));
  } else {
    localStorage.removeItem("commitai_user");
  }
}

export function logout() {
  localStorage.removeItem("commitai_token");
  localStorage.removeItem("commitai_user");
  window.location.href = "/login";
}

export async function request(
  path,
  { method = "GET", body, headers = {}, timeout = 90000 } = {},
) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  const token = getToken();
  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  try {
    const response = await fetch(path, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
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
      if (
        response.status === 401 &&
        !path.startsWith("/api/auth/login") &&
        !path.startsWith("/api/auth/register")
      ) {
        logout();
      }

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