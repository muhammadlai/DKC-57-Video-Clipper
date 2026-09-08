import { NextResponse, type NextRequest } from "next/server";

const COOKIE_NAME = "aitzaz_session";

/**
 * Lightweight route gating based on cookie *presence* (verification happens
 * server-side in the API on every request).
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = !!request.cookies.get(COOKIE_NAME);

  const isAuthPage = pathname === "/login" || pathname === "/register";
  const isProtected =
    !isAuthPage &&
    pathname !== "/" && // root redirects itself
    !pathname.startsWith("/api");

  if (isProtected && !hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isAuthPage && hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
