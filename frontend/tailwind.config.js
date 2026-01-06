/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Dark mode focused color palette (WCAG-compliant)
        dark: {
          bg: {
            primary: '#121212',    // Main background (softer than #0a0a0a)
            secondary: '#1a1a1a',  // Card backgrounds
            tertiary: '#262626',   // Elevated surfaces
            hover: '#2d2d2d',      // Hover states
          },
          border: {
            primary: '#333333',    // Default borders
            secondary: '#404040',  // Hover borders
            accent: '#4a5568',     // Active borders
          },
          text: {
            primary: '#f5f5f5',    // Primary text (15.4:1 ratio)
            secondary: '#d1d5db',  // Secondary text (10.5:1)
            muted: '#9ca3af',      // Muted text (7.5:1)
            disabled: '#6b7280',   // Disabled (4.6:1)
          },
          // Legacy aliases for backward compatibility
          primary: '#121212',
          secondary: '#1a1a1a',
          tertiary: '#262626',
        },
        accent: {
          blue: {
            DEFAULT: '#3b82f6',
            light: '#60a5fa',
            dark: '#2563eb',
          },
          purple: {
            DEFAULT: '#8b5cf6',
            light: '#a78bfa',
            dark: '#7c3aed',
          },
          green: {
            DEFAULT: '#22c55e',
            light: '#4ade80',
            dark: '#16a34a',
          },
        },
      },
      animation: {
        'shimmer': 'shimmer 2s infinite linear',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'scale-in': 'scaleIn 0.2s ease-out',
        'gradient': 'gradient 3s ease infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        gradient: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
      },
      backgroundSize: {
        'auto': 'auto',
        'cover': 'cover',
        'contain': 'contain',
        '200%': '200% auto',
      },
      boxShadow: {
        'glow-blue': '0 0 20px rgba(59, 130, 246, 0.3)',
        'glow-purple': '0 0 20px rgba(139, 92, 246, 0.3)',
        'glow-green': '0 0 20px rgba(34, 197, 94, 0.3)',
      },
    },
  },
  plugins: [],
};















