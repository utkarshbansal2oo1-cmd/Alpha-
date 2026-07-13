/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // A near-black, slightly blue-shifted base -- the same family of
        // dark used by Linear/Arc/Vercel's own apps, not pure #000 (which
        // reads as "unfinished" rather than "cinematic").
        void: {
          950: "#05060a",
          900: "#0a0c14",
          800: "#10131d",
          700: "#161a27",
          600: "#1f2434",
        },
        ink: {
          100: "#f5f6fa",
          300: "#c7cbdb",
          500: "#8b90a8",
          700: "#565c74",
        },
        accent: {
          400: "#8b7bff",
          500: "#6e5cf0",
          600: "#5645d1",
        },
        signal: {
          // Used sparingly for live/active states -- discovery in
          // progress, a connector actively searching.
          green: "#3ddc97",
          amber: "#f0b64c",
          red: "#f2555a",
        },
      },
      fontFamily: {
        display: ["'Inter var'", "Inter", "-apple-system", "sans-serif"],
      },
      fontSize: {
        hero: ["clamp(2.75rem, 6vw, 5.5rem)", { lineHeight: "1.02", letterSpacing: "-0.03em" }],
        "display-lg": ["clamp(2rem, 3.5vw, 3rem)", { lineHeight: "1.08", letterSpacing: "-0.02em" }],
      },
      backdropBlur: {
        xs: "2px",
      },
      boxShadow: {
        glass: "0 1px 0 0 rgba(255,255,255,0.06) inset, 0 8px 40px -12px rgba(0,0,0,0.6)",
        glow: "0 0 0 1px rgba(139,123,255,0.25), 0 0 60px -10px rgba(110,92,240,0.45)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 2.2s linear infinite",
      },
    },
  },
  plugins: [],
}
