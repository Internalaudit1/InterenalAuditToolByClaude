import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { defaultWorkspacePath, isRouteAllowed } from "@/lib/navigation";

const PUBLIC_PATHS = ["/login", "/forbidden"];

function externalRedirectUrl(request: NextRequest, pathname: string) {
  const url = request.nextUrl.clone();
  const forwardedHost = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? request.nextUrl.host;
  const forwardedProto = request.headers.get("x-forwarded-proto") ?? request.nextUrl.protocol.replace(":", "");
  url.protocol = `${forwardedProto}:`;
  url.host = forwardedHost;
  url.pathname = pathname;
  url.search = "";
  return url;
}

function readSessionPermissions(request: NextRequest) {
  const rawUser = request.cookies.get("dia_user")?.value ?? "";
  if (!rawUser) return [];
  try {
    const user = JSON.parse(decodeURIComponent(rawUser)) as { permissions?: string[] };
    return Array.isArray(user.permissions) ? user.permissions : [];
  } catch {
    return [];
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get("dia_access_token")?.value ?? "";
  const permissions = readSessionPermissions(request);

  if (PUBLIC_PATHS.some((path) => pathname.startsWith(path))) {
    return NextResponse.next();
  }

  if (!accessToken || !permissions.length) {
    return NextResponse.redirect(externalRedirectUrl(request, "/login"));
  }

  if (pathname === "/") {
    return NextResponse.redirect(externalRedirectUrl(request, defaultWorkspacePath(permissions)));
  }

  if (pathname === "/planning") {
    return NextResponse.redirect(externalRedirectUrl(request, permissions.includes("planning:manage") ? "/planning/process-risk-mappings" : "/planning/audit-plans"));
  }

  if (pathname === "/knowledge-library") {
    return NextResponse.redirect(externalRedirectUrl(request, "/knowledge-library/process-universe"));
  }

  if (pathname === "/masters") {
    return NextResponse.redirect(externalRedirectUrl(request, "/masters/countries"));
  }

  if (pathname === "/admin") {
    if (permissions.includes("activity_logs:view")) {
      return NextResponse.redirect(externalRedirectUrl(request, "/admin/activity-logs"));
    }
    if (permissions.includes("users:view")) {
      return NextResponse.redirect(externalRedirectUrl(request, "/admin/users"));
    }
    if (permissions.includes("roles:view")) {
      return NextResponse.redirect(externalRedirectUrl(request, "/admin/roles"));
    }
    return NextResponse.redirect(externalRedirectUrl(request, "/forbidden"));
  }

  if (!isRouteAllowed(pathname, permissions)) {
    return NextResponse.redirect(externalRedirectUrl(request, "/forbidden"));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"]
};
