/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#F5F7FA',
        primary: '#12355B',
        secondary: '#1D7874',
        accent: '#F4A261',
        cards: '#FFFFFF',
        text: '#17202A',
      }
    },
  },
  plugins: [],
}
