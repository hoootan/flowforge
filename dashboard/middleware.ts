import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that don't require authentication
const PUBLIC_ROUTES = ["/login"];

// Routes that should be accessible without full auth check (static assets, etc.)
const EXCLUDED_ROUTES = [
  "/_next",
  "/api",
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip auth entirely in mock mode (local dev without backend)
  if (process.env.NEXT_PUBLIC_USE_MOCK === "true" && process.env.NODE_ENV === "development") {
    return NextResponse.next();
  }

  // Skip middleware for excluded routes
  if (EXCLUDED_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Allow public routes
  if (PUBLIC_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check for auth token in localStorage (via cookie set by client)
  // Note: We use a custom cookie that the client sets when logging in
  // This is because localStorage is not accessible in middleware
  const authCookie = request.cookies.get("flowforge-auth-token");

  // If no auth cookie, redirect to login
  if (!authCookie?.value) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
