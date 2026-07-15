import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

// Next.js 16 renamed Middleware to Proxy. This guards dashboard routes and
// bounces authenticated users away from the auth pages (optimistic check).
export async function proxy(request: NextRequest) {
  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
  });
  const { pathname } = request.nextUrl;
  const isAuthPage = pathname === "/login" || pathname === "/register";

  if (!token && !isAuthPage) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (token && isAuthPage) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  // Admin section: logged in but not an admin → bounce to dashboard. The real
  // gate is the backend's require_admin; this just hides the UI.
  if (pathname.startsWith("/admin") && token?.role !== "admin") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/api-keys/:path*",
    "/models/:path*",
    "/logs/:path*",
    "/playground/:path*",
    "/admin/:path*",
    "/login",
    "/register",
  ],
};
