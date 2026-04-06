'use client';

/**
 * LoginForm — Google OAuth + email magic link + email/password auth.
 * Mirrors pages/login.tsx auth flow for App Router.
 */
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { signInWithGoogle, signInWithMagicLink, signInWithEmailPassword, supabase } from '@/lib/supabase';

interface Message {
  type: 'success' | 'error';
  text: string;
}

export function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [usePassword, setUsePassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [message, setMessage] = useState<Message | null>(null);
  const router = useRouter();

  // Check existing session on mount
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        router.replace('/dashboard');
      } else {
        setAuthLoading(false);
      }
    });
  }, [router]);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setMessage(null);
    const { error } = await signInWithGoogle();
    if (error) {
      setMessage({ type: 'error', text: error.message });
      setLoading(false);
    }
    // OAuth redirects — no success handling needed here
  };

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setMessage({ type: 'error', text: 'Please enter your email address' });
      return;
    }

    setLoading(true);
    setMessage(null);

    if (usePassword) {
      if (!password) {
        setMessage({ type: 'error', text: 'Please enter your password' });
        setLoading(false);
        return;
      }
      const { error } = await signInWithEmailPassword(email, password);
      setLoading(false);
      if (error) {
        setMessage({ type: 'error', text: error.message });
      } else {
        router.push('/dashboard');
      }
    } else {
      const { error } = await signInWithMagicLink(email);
      setLoading(false);
      if (error) {
        setMessage({ type: 'error', text: error.message });
      } else {
        setMessage({ type: 'success', text: 'Check your email for a magic link to sign in!' });
        setEmail('');
      }
    }
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex items-center gap-3 text-lg text-muted-foreground">
          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-background/80 backdrop-blur-xl p-8 shadow-2xl">
      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          Research Agent
        </h1>
        <p className="mt-2 text-muted-foreground text-sm leading-relaxed max-w-xs mx-auto">
          Turn videos and articles into source-cited scripts — with the angle nobody else covered.
        </p>
      </div>

      {/* Google OAuth */}
      <button
        onClick={handleGoogleLogin}
        disabled={loading}
        className="flex w-full items-center justify-center gap-3 rounded-xl border border-border bg-card px-4 py-3.5 text-foreground transition-all duration-200 hover:bg-muted hover:border-border disabled:cursor-not-allowed disabled:opacity-50"
      >
        <GoogleIcon />
        Continue with Google
      </button>

      <div className="my-6 flex items-center">
        <div className="flex-grow border-t border-border" />
        <span className="mx-4 text-sm text-muted-foreground">or</span>
        <div className="flex-grow border-t border-border" />
      </div>

      {/* Email Form */}
      <form onSubmit={handleEmailLogin}>
        <div className="mb-4">
          <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-muted-foreground">
            Email address
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            className="w-full rounded-xl border border-border bg-card px-4 py-3.5 text-foreground placeholder-gray-400 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            disabled={loading}
          />
        </div>

        {usePassword && (
          <div className="mb-4">
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-muted-foreground">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              className="w-full rounded-xl border border-border bg-card px-4 py-3.5 text-foreground placeholder-gray-400 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              disabled={loading}
            />
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-4 py-3.5 font-medium text-white shadow-lg shadow-blue-500/20 transition-all duration-200 hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {usePassword ? 'Signing in...' : 'Sending...'}
            </span>
          ) : (
            usePassword ? 'Sign In' : 'Send Magic Link'
          )}
        </button>

        <button
          type="button"
          onClick={() => { setUsePassword(!usePassword); setMessage(null); setPassword(''); }}
          className="mt-3 w-full text-center text-sm text-muted-foreground hover:text-muted-foreground transition-colors"
        >
          {usePassword ? 'Use magic link instead' : 'Use password instead'}
        </button>
      </form>

      {/* Message — role="alert" announces errors immediately to screen readers */}
      <div
        role="alert"
        aria-live={message?.type === 'error' ? 'assertive' : 'polite'}
        aria-atomic="true"
      >
        {message && (
          <div
            className={`mt-4 rounded-xl p-4 text-sm ${
              message.type === 'success'
                ? 'border border-green-500/30 bg-green-900/30 text-green-300'
                : 'border border-red-500/30 bg-red-900/30 text-red-300'
            }`}
          >
            {message.text}
          </div>
        )}
      </div>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        By signing in, you agree to our{' '}
        <a href="/terms" className="underline hover:text-foreground transition-colors">Terms of Service</a>
        {' '}and{' '}
        <a href="/privacy" className="underline hover:text-foreground transition-colors">Privacy Policy</a>.
      </p>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}
