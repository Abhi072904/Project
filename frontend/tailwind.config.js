/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#EFF1EA',
        'paper-raised': '#F7F8F3',
        ink: '#1B2A3D',
        'ink-soft': '#5B6B7A',
        line: '#D8DACE',
        leak: '#D6482F',
        'leak-soft': '#F3DCD5',
        saved: '#2F6F4E',
        'saved-soft': '#DCE9E0',
        stamp: '#2B3A67',
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
