/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Manrope', 'Inter', 'system-ui', 'sans-serif'], mono: ['JetBrains Mono', 'ui-monospace', 'monospace'] },
      colors: {
        ink: { 950: '#05080f', 900: '#0a0f1c', 800: '#0f1628', 700: '#16203a', 600: '#22304f' },
        cyan: { 300: '#7deaff', 400: '#38d9f5', 500: '#12bfe0' },
        amber: { 300: '#ffd27a', 400: '#ffb547', 500: '#f59e0b' },
        risk: { high: '#ff5c6c', med: '#ffb547', low: '#34d399' },
      },
    },
  },
  plugins: [],
}
