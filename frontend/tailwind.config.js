/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#2563eb",
        sidebar: "#1e293b",
        "sidebar-hover": "#334155",
      },
    },
  },
  plugins: [],
};
