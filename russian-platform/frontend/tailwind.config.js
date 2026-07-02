/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef4ff',
          100: '#dbe6fe',
          500: '#4f6ef7',
          600: '#3a53e0',
          700: '#2f42b8',
          900: '#232e6b',
        },
      },
    },
  },
  plugins: [],
};
