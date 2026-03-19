/**
 * Next.js middleware — real auth enforcement using @supabase/ssr.
 *
 * Public routes: /login, /shared/*, /_next/*, /favicon.ico, /mockups/*, /api/*
 * Protected (app) routes: redirect to /login if no valid session
 * Protected (admin) routes: redirect to /dashboard if not admin role
 */
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { createServerClient } from '@supabase/ssr';

// Routes that never require authentication
const PUBLIC_ROUTES = ['/login', '/favicon.ico'];
const PUBLIC_PREFIXES = ['/shared/', '/_next/', '/mockups/', '/api/'];

function isPublicRoute(pathname: string): boolean {
  if (PUBLIC_ROUTES.includes(pathname)) return true;
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always pass through public routes
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }


  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

  // Create a response we can mutate for cookie refresh
  let response = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value)
        );
        // Refresh the response with the updated request cookies
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        );
      },
    },
  });

  // Refresh session — getUser() validates the session server-side
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isAdminRoute = pathname.startsWith('/(admin)') || pathname.startsWith('/admin');
  const isAppRoute = pathname.startsWith('/(app)') || (!isPublicRoute(pathname) && !isAdminRoute);

  // No session → redirect to login for any protected route
  if (!user) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = '/login';
    return NextResponse.redirect(loginUrl);
  }

  // Admin routes — check role in user metadata
  if (isAdminRoute) {
    const role = user.app_metadata?.role || user.user_metadata?.role;
    if (role !== 'admin') {
      const dashboardUrl = request.nextUrl.clone();
      dashboardUrl.pathname = '/dashboard';
      return NextResponse.redirect(dashboardUrl);
    }
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all paths EXCEPT:
     * - _next/static (static files)
     * - _next/image (image optimisation)
     * - favicon.ico
     * - mockups (public static assets)
     */
    '/((?!_next/static|_next/image|favicon.ico|mockups).*)',
  ],
};
