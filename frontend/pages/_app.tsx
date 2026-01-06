import type { AppProps } from 'next/app';
import { AuthProvider } from '../components/AuthProvider';
import ErrorBoundary from '../components/ErrorBoundary';
import '../styles/globals.css';

// Validate critical environment variables in production
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production') {
  if (!process.env.NEXT_PUBLIC_API_URL) {
    console.error(
      '[Research Agent] NEXT_PUBLIC_API_URL is not set. API requests will fail.'
    );
  }
}

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Log to console in development, could be sent to monitoring service in production
        if (process.env.NODE_ENV === 'development') {
          console.error('App Error Boundary caught:', error, errorInfo);
        }
      }}
    >
      <AuthProvider>
        <Component {...pageProps} />
      </AuthProvider>
    </ErrorBoundary>
  );
}









