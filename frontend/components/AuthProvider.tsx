/**
 * Authentication context provider for the application.
 * Wraps the app to provide auth state to all components.
 */
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { useRouter } from 'next/router';
import { supabase, signOut as supabaseSignOut, getAccessToken } from '../lib/supabase';
import { useJobsStore } from '../store/jobs';
import { useSettingsStore } from '../store/settings';
import { API_URL } from '../lib/constants';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  isAdmin: boolean;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  loading: true,
  isAdmin: false,
  signOut: async () => {},
});

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  // Dev mode bypass - skip auth when NEXT_PUBLIC_DISABLE_AUTH=true
  const isDevBypass = process.env.NEXT_PUBLIC_DISABLE_AUTH === 'true';

  // All hooks must be called unconditionally (Rules of Hooks)
  const [user, setUser] = useState<User | null>(
    isDevBypass ? ({ id: 'dev-user', email: 'dev@local.test' } as User) : null
  );
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(!isDevBypass);
  const [isAdmin, setIsAdmin] = useState(isDevBypass);
  const router = useRouter();

  // Check admin status when user changes
  const checkAdminStatus = useCallback(async (userId: string | undefined) => {
    if (isDevBypass) return; // Skip in dev mode
    if (!userId) {
      setIsAdmin(false);
      return;
    }
    try {
      const token = await getAccessToken();
      if (!token) {
        setIsAdmin(false);
        return;
      }
      const response = await fetch(`${API_URL}/admin/check`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setIsAdmin(data.is_admin === true);
      } else {
        setIsAdmin(false);
      }
    } catch {
      setIsAdmin(false);
    }
  }, [isDevBypass]);

  useEffect(() => {
    // Skip auth setup in dev bypass mode
    if (isDevBypass) return;

    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      checkAdminStatus(session?.user?.id);
      setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      checkAdminStatus(session?.user?.id);
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [isDevBypass, checkAdminStatus]);

  const handleSignOut = async () => {
    if (isDevBypass) return; // No-op in dev mode
    await supabaseSignOut();
    setIsAdmin(false);
    // Clear stores on logout
    useJobsStore.getState().clearJobs();
    router.push('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        isAdmin,
        signOut: handleSignOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Higher-order component for protected routes.
 * Redirects to login if user is not authenticated.
 */
interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <>{children}</>;
}

/**
 * Higher-order component for admin-only routes.
 * Redirects to dashboard if user is not an admin.
 */
export function AdminProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, loading, isAdmin } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    } else if (!loading && user && !isAdmin) {
      router.push('/dashboard');
    }
  }, [user, loading, isAdmin, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!user || !isAdmin) {
    return null;
  }

  return <>{children}</>;
}
