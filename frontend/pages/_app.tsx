import type { AppProps } from 'next/app';
import { AuthProvider } from '../components/AuthProvider';
import { ThemeProvider } from '../contexts/ThemeContext';
import '../styles/globals.css';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Component {...pageProps} />
      </AuthProvider>
    </ThemeProvider>
  );
}

