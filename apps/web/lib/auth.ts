import { deleteCookie, readCookie, writeCookie } from "@/lib/cookies";

export type SessionUser = {
  id: number;
  username: string;
  email: string;
  full_name: string;
  roles: string[];
  permissions: string[];
};

export function setSession(accessToken: string, refreshToken: string, user: SessionUser) {
  writeCookie("dia_access_token", accessToken);
  writeCookie("dia_refresh_token", refreshToken);
  writeCookie("dia_role", user.roles[0] ?? "");
  writeCookie("dia_user", JSON.stringify(user));
}

export function clearSession() {
  deleteCookie("dia_access_token");
  deleteCookie("dia_refresh_token");
  deleteCookie("dia_role");
  deleteCookie("dia_user");
}

export function getSessionUser(): SessionUser | null {
  const raw = readCookie("dia_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as SessionUser;
  } catch {
    return null;
  }
}

export function getPrimaryRole() {
  return readCookie("dia_role");
}

export function getSessionPermissions() {
  return getSessionUser()?.permissions ?? [];
}

export function hasPermission(permission: string) {
  return getSessionPermissions().includes(permission);
}

export function getAccessToken() {
  return readCookie("dia_access_token");
}

export function getRefreshToken() {
  return readCookie("dia_refresh_token");
}
