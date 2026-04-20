import { API_BASE_URL } from "@/lib/config";
import { clearSession, getAccessToken, getRefreshToken, setSession, type SessionUser } from "@/lib/auth";

type ApiOptions = RequestInit & {
  isRaw?: boolean;
};

function redirectToLogin() {
  clearSession();
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function refreshTokens() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  if (!response.ok) {
    redirectToLogin();
    return false;
  }
  const data = await response.json();
  setSession(data.access_token, data.refresh_token, data.user as SessionUser);
  return true;
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const token = getAccessToken();
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {})
    }
  });

  if (response.status === 401) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return apiFetch<T>(path, options);
    }
    redirectToLogin();
    throw new Error("Session expired. Please sign in again.");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Request failed");
  }

  if (options.isRaw) {
    return (response as unknown) as T;
  }
  return response.json() as Promise<T>;
}

async function downloadBlobResponse(response: Response, filename: string) {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? payload.message ?? "Download failed");
  }
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(href);
}

export async function apiDownload(path: string, filename: string) {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });
  if (response.status === 401) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return apiDownload(path, filename);
    }
    redirectToLogin();
    throw new Error("Session expired. Please sign in again.");
  }
  await downloadBlobResponse(response, filename);
}

export async function apiDownloadPost(path: string, filename: string, body: BodyInit) {
  const token = getAccessToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body
  });
  if (response.status === 401) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return apiDownloadPost(path, filename, body);
    }
    redirectToLogin();
    throw new Error("Session expired. Please sign in again.");
  }
  await downloadBlobResponse(response, filename);
}
