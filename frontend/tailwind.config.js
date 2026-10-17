/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter Variable"', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Fraunces Variable"', 'Georgia', 'ui-serif', 'serif'],
      },
      colors: {
        ink: '#12243A',
        teal: { 50: '#EFFAF8', 100: '#D8F3EE', 500: '#178C81', 600: '#117369' },
      },
      transitionTimingFunction: { out: 'cubic-bezier(.2, .7, .2, 1)', precise: 'cubic-bezier(.65, 0, .35, 1)' },
      transitionDuration: { fast: '160ms', base: '320ms', slow: '700ms' },
      // Softer, rounder defaults so every card on every page loses the hard boxed look.
      borderRadius: { lg: '0.875rem', xl: '1.125rem', '2xl': '1.5rem', '3xl': '2rem' },
      boxShadow: {
        sm: '0 8px 28px rgba(18, 36, 58, 0.06)',
        soft: '0 24px 70px rgba(18, 36, 58, 0.10)',
        glow: '0 20px 60px -10px rgba(23, 140, 129, 0.35)',
      },
    },
  },
  plugins: [],
};
