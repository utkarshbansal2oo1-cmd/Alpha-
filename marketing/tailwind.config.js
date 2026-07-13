/** Tailwind config implementing docs/MARKETING_SITE_DESIGN_SYSTEM.md's
 * color system, typography scale, and glass-plane elevation tokens exactly
 * as specified -- values are not approximated or "close enough". */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#050816",
        plane1: "rgba(255,255,255,0.02)",
        plane2: "rgba(255,255,255,0.04)",
        plane3: "rgba(255,255,255,0.06)",
        "accent-blue": "#3B82F6",
        "accent-purple": "#8B5CF6",
        "accent-cyan": "#22D3EE",
        "text-primary": "#F8FAFC",
        "text-secondary": "#94A3B8",
        "text-tertiary": "#64748B",
        "match-green": "#34D399",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      fontSize: {
        "hero-desktop": ["88px", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        "hero-mobile": ["44px", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
        "section-desktop": ["56px", { lineHeight: "1.1", letterSpacing: "-0.015em" }],
        "section-mobile": ["32px", { lineHeight: "1.15", letterSpacing: "-0.015em" }],
        "body-large": ["22px", { lineHeight: "1.5" }],
        caption: ["13px", { lineHeight: "1.4", letterSpacing: "0.08em" }],
      },
      backgroundImage: {
        "accent-gradient":
          "linear-gradient(135deg, #3B82F6 0%, #8B5CF6 50%, #22D3EE 100%)",
      },
      backdropBlur: {
        plane1: "20px",
        plane2: "24px",
      },
      boxShadow: {
        "glow-blue": "0 0 80px rgba(59,130,246,0.08)",
        "glow-card": "0 0 40px rgba(139,92,246,0.12)",
      },
    },
  },
  plugins: [],
};
