/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0f172a",
          secondary: "#475569",
          muted: "#64748b",
          subtle: "#94a3b8",
        },
        canvas: "#f8fafc",
        surface: {
          DEFAULT: "#ffffff",
          subtle: "#f8fafc",
          muted: "#f1f5f9",
          border: "#e2e8f0",
        },
        line: {
          DEFAULT: "#e2e8f0",
          subtle: "#f1f5f9",
          strong: "#cbd5e1",
        },
        accent: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          DEFAULT: "#0f75c6",
          500: "#1683d8",
          600: "#0f75c6",
          700: "#0a5d9e",
          800: "#07487a",
          900: "#043358",
        },
        secondary: {
          50: "#eef2ff",
          100: "#e0e7ff",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
        },
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#1683d8",
          600: "#0f75c6",
          700: "#0a5d9e",
          800: "#084b7d",
          900: "#063a61",
        },
        signal: {
          amber: {
            bg: "#fffbeb",
            border: "#fcd34d",
            text: "#b45309",
            badge: "#fef3c7",
          },
          red: {
            bg: "#fef2f2",
            border: "#fca5a5",
            text: "#b91c1c",
            badge: "#fee2e2",
          },
          green: {
            bg: "#ecfdf5",
            border: "#6ee7b7",
            text: "#047857",
            badge: "#d1fae5",
          },
          blue: {
            bg: "#eff6ff",
            border: "#93c5fd",
            text: "#1d4ed8",
            badge: "#dbeafe",
          },
        },
        paper: "#f6f8fa",
        warning: "#fff8d9",
        warningBorder: "#e4cf69",
      },
      boxShadow: {
        xs: "0 1px 2px 0 rgba(15, 23, 42, 0.04)",
        sm: "0 1px 3px 0 rgba(15, 23, 42, 0.07), 0 1px 2px -1px rgba(15, 23, 42, 0.05)",
        md: "0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)",
        lg: "0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04)",
        card: "0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)",
        "card-hover": "0 10px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04)",
        panel: "0 1px 3px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.04)",
      },
      keyframes: {
        "pulse-scale": {
          "0%, 100%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.06)" },
        },
        "fade-slide-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fill-progress": {
          "0%": { width: "0%" },
          "100%": { width: "100%" },
        },
      },
      animation: {
        "pulse-scale": "pulse-scale 0.35s ease-in-out",
        "fade-slide-in": "fade-slide-in 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards",
      },
    },
  },
  plugins: [],
};

