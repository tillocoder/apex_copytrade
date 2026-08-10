/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        apex: {
          bg: "#0E1116",
          bgSecondary: "#151A21",
          surface: "#1B222C",
          hover: "#242D39",
          border: "#2C3643",
          divider: "#3A4655",
          text: "#F5F7FA",
          textSecondary: "#B5BDC8",
          muted: "#7C8796",
          disabled: "#596272",
          accent: "#5EA8FF",
          success: "#22C55E",
          danger: "#EF4444",
          warning: "#F59E0B",
          info: "#38BDF8",
          ai: "#8B5CF6",
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        panel: '12px',
        btn: '10px',
      },
      boxShadow: {
        subtle: "0 1px 3px 0 rgba(0, 0, 0, 0.25), 0 1px 2px -1px rgba(0, 0, 0, 0.25)",
        panel: "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.3)",
        focus: "0 0 0 2px rgba(94, 168, 255, 0.4)",
      }
    },
  },
  plugins: [],
}
