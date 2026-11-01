/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#090d16',
        card: '#0f172a',
        'card-foreground': '#f8fafc',
        popover: '#0f172a',
        'popover-foreground': '#f8fafc',
        primary: {
          DEFAULT: '#0ea5e9',
          foreground: '#f8fafc',
          glow: 'rgba(14, 165, 233, 0.25)',
        },
        secondary: {
          DEFAULT: '#1e293b',
          foreground: '#94a3b8',
        },
        muted: {
          DEFAULT: '#141e33',
          foreground: '#64748b',
        },
        accent: {
          DEFAULT: '#06b6d4',
          foreground: '#090d16',
        },
        safe: {
          DEFAULT: '#10b981',
          foreground: '#042f2e',
          glow: 'rgba(16, 185, 129, 0.25)',
        },
        warning: {
          DEFAULT: '#f59e0b',
          foreground: '#451a03',
          glow: 'rgba(245, 158, 11, 0.25)',
        },
        danger: {
          DEFAULT: '#ef4444',
          foreground: '#450a0a',
          glow: 'rgba(239, 68, 68, 0.25)',
        },
        border: '#1e293b',
        input: '#1e293b',
        ring: '#0ea5e9',
        panel: {
          bg: '#0c1322',
          border: '#1a2744',
          header: '#111c33',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.6', transform: 'scale(1.05)' },
        },
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(1000%)' },
        },
      },
      animation: {
        'pulse-glow': 'pulseGlow 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        scanline: 'scanline 8s linear infinite',
      },
    },
  },
  plugins: [],
}
