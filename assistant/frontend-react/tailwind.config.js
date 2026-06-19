/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // HELIOS palette — mirrors the original renderer design tokens.
        obsidian: '#0E0E10',
        charcoal: '#1A1A1E',
        slate: '#242428',
        ivory: '#F2EDE4',
        warmgray: '#8C8880',
        gold: '#B8976A',
        helgreen: '#6FA98C',
        helred: '#C97A6A',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderColor: {
        hairline: 'rgba(242, 237, 228, 0.10)',
      },
      boxShadow: {
        hud: '0 8px 40px rgba(0,0,0,0.45)',
      },
      keyframes: {
        pulseDot: {
          '0%,100%': { opacity: '1' },
          '50%': { opacity: '0.35' },
        },
      },
      animation: {
        pulseDot: 'pulseDot 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
