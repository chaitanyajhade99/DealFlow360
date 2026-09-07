/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        // QuoteIt brand — "Executive Precision" design system from Stitch
        brand: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",  // Primary — indigo
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        // Surface / Canvas
        canvas: "#f8f9ff",
        surface: {
          DEFAULT: "#ffffff",
          subtle:  "#f8f9ff",
          muted:   "#eff4ff",
          border:  "#e2e8f0",
        },
        // Sidebar — deep navy
        sidebar: {
          bg:     "#0f172a",
          hover:  "rgba(255,255,255,0.05)",
          active: "#4f46e5",
          text:   "rgba(255,255,255,0.75)",
          label:  "rgba(255,255,255,0.35)",
          border: "rgba(255,255,255,0.08)",
        },
        // Ink / text
        ink: {
          DEFAULT:   "#0b1c30",
          secondary: "#475569",
          muted:     "#64748b",
          subtle:    "#94a3b8",
          inverted:  "#ffffff",
        },
        // Line / border
        line: {
          DEFAULT: "#e2e8f0",
          subtle:  "#f1f5f9",
          strong:  "#cbd5e1",
        },
        // Semantic signals
        signal: {
          green:  { bg: "#ecfdf5", border: "#6ee7b7", text: "#047857", badge: "#d1fae5" },
          amber:  { bg: "#fffbeb", border: "#fcd34d", text: "#b45309", badge: "#fef3c7" },
          red:    { bg: "#fef2f2", border: "#fca5a5", text: "#b91c1c", badge: "#fee2e2" },
          blue:   { bg: "#eff6ff", border: "#93c5fd", text: "#1d4ed8", badge: "#dbeafe" },
          indigo: { bg: "#eef2ff", border: "#a5b4fc", text: "#4338ca", badge: "#e0e7ff" },
          violet: { bg: "#f5f3ff", border: "#c4b5fd", text: "#6d28d9", badge: "#ede9fe" },
        },
        // Keep legacy aliases for existing component compatibility
        accent:    { DEFAULT: "#4f46e5", 500: "#6366f1", 600: "#4f46e5", 700: "#4338ca" },
        secondary: { 500: "#6366f1",     600: "#4f46e5",  700: "#4338ca" },
        // Status colors used in StatusBadge
        paper:          "#f6f8fa",
        warning:        "#fff8d9",
        warningBorder:  "#e4cf69",
      },
      // Sidebar layout
      width: {
        sidebar:        "240px",
        "sidebar-icon": "64px",
      },
      minWidth: {
        sidebar:        "240px",
        "sidebar-icon": "64px",
      },
      boxShadow: {
        xs:          "0 1px 2px 0 rgba(15, 23, 42, 0.04)",
        sm:          "0 1px 3px 0 rgba(15, 23, 42, 0.07), 0 1px 2px -1px rgba(15, 23, 42, 0.05)",
        md:          "0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05)",
        lg:          "0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.04)",
        xl:          "0 20px 25px -5px rgba(15,23,42,0.10), 0 8px 10px -6px rgba(15,23,42,0.06)",
        card:        "0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)",
        "card-hover":"0 10px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.04)",
        panel:       "0 1px 3px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.04)",
        modal:       "0 25px 50px -12px rgba(15, 23, 42, 0.25)",
        "inset-top": "inset 0 1px 0 rgba(255,255,255,0.06)",
      },
      keyframes: {
        "fade-slide-in": {
          "0%":   { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-in-left": {
          "0%":   { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "pulse-scale": {
          "0%, 100%": { transform: "scale(1)" },
          "50%":       { transform: "scale(1.06)" },
        },
        "fill-progress": {
          "0%":   { width: "0%" },
          "100%": { width: "100%" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "toast-in": {
          "0%":   { opacity: "0", transform: "translateX(100%)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "badge-pop": {
          "0%":   { transform: "scale(0.85)", opacity: "0" },
          "60%":  { transform: "scale(1.05)" },
          "100%": { transform: "scale(1)",    opacity: "1" },
        },
      },
      animation: {
        "fade-slide-in": "fade-slide-in 0.22s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "fade-in":       "fade-in 0.18s ease-out forwards",
        "slide-in-left": "slide-in-left 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "pulse-scale":   "pulse-scale 0.35s ease-in-out",
        shimmer:         "shimmer 1.6s linear infinite",
        "toast-in":      "toast-in 0.28s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "badge-pop":     "badge-pop 0.2s cubic-bezier(0.34, 1.56, 0.64, 1) forwards",
      },
    },
  },
  plugins: [],
};
