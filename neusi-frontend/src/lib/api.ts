// src/lib/api.ts
const API = process.env.NEXT_PUBLIC_API_BASE!;

/**
 * ✅ Obtiene el token CSRF desde el backend y lo devuelve en el body JSON.
 * Django también setea la cookie 'csrftoken', pero no la leemos con document.cookie
 * porque el navegador no permite acceder a cookies de otro dominio.
 */
function getCookie(name: string) {
  const m = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return m ? m[2] : "";
}

export async function getCsrf(): Promise<string> {
  const res = await fetch(`${API}/api/auth/csrf/`, { credentials: "include" });
  // El backend devuelve { detail, csrfToken }
  const data = await res.json().catch(() => ({}));
  // fallback por si algún navegador no deja leer el body
  return data?.csrfToken || getCookie("csrftoken") || "";
}

/**
 * ✅ Envía las credenciales al backend usando el token CSRF recibido por JSON.
 */
export async function login(username: string, password: string) {
  const csrftoken = await getCsrf(); // obtenemos el token del body JSON

  const res = await fetch(`${API}/api/auth/login/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrftoken ?? "", // se envía al header
    },
    body: JSON.stringify({ username, password }),
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) throw new Error(data.error || "Error al iniciar sesión");
  return data;
}

/**
 * ✅ Consulta la sesión actual (usuario logueado).
 */
export async function me() {
  try {
    const res = await fetch(`${API}/api/auth/me/`, { credentials: "include" });
    if (!res.ok) return null; // 302 o 403 → no autenticado
    return await res.json();
  } catch {
    return null; // error de red o CORS → sesión inválida
  }
}

/**
 * ✅ Cierra la sesión del usuario actual.
 */
export async function logout() {
  // Asegura token fresco y cookie presente
  const csrftoken = await getCsrf();
  const res = await fetch(`${API}/api/auth/logout/`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRFToken": csrftoken },
  });
  if (!res.ok) throw new Error("No se pudo cerrar sesión");
  return true;
}