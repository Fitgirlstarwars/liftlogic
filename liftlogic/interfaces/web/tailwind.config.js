/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        industrial: {
          50: '#f4f6f8',
          100: '#e4e8eb',
          200: '#c9d1d9',
          300: '#aab6c3',
          400: '#8495a8',
          500: '#64748b', // Slate-500
          600: '#475569', // Slate-600
          700: '#334155', // Slate-700
          800: '#1e293b', // Slate-800
          900: '#0f172a', // Slate-900 (Dark Blue-Gray)
        },
        safety: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b', // Amber-500 (Orange)
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        }
      }
    },
  },
  plugins: [],
};
