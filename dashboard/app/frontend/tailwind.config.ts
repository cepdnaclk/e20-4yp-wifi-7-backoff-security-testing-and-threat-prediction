import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'neu-bg': '#e8edf2',
        'neu-card': '#e8edf2',
        'neu-text': '#2d3748',
        'neu-muted': '#718096',
        'brand': '#6392fa',
        'brand-dark': '#4a7bf0',
        'normal': '#4caf87',
        'attack': '#e85d6a',
        'warning': '#f59e0b',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'neu': '20px',
        'neu-sm': '14px',
        'pill': '999px',
      },
      boxShadow: {
        'neu-raised': '8px 8px 16px rgba(166,180,200,0.7), -8px -8px 16px rgba(255,255,255,0.8)',
        'neu-inset': 'inset 4px 4px 8px rgba(166,180,200,0.6), inset -4px -4px 8px rgba(255,255,255,0.7)',
        'neu-flat': '4px 4px 8px rgba(166,180,200,0.5), -4px -4px 8px rgba(255,255,255,0.6)',
        'neu-hover': '10px 10px 20px rgba(166,180,200,0.8), -10px -10px 20px rgba(255,255,255,0.9)',
      },
    },
  },
  plugins: [],
} satisfies Config
