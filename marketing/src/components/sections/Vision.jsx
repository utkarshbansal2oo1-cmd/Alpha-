import { motion } from "framer-motion";
import SectionHeading from "../ui/SectionHeading";
import { useScrollReveal } from "../../hooks/useScrollReveal";

const ROADMAP = [
  { label: "Today", detail: "MVP", isToday: true },
  { label: "AlphaRecrewt Integration", detail: "Shortlist straight into assessments" },
  { label: "Resume Intelligence", detail: "Parse and enrich raw resumes" },
  { label: "Enterprise AI Hiring Platform", detail: "LinkedIn, ATS, and GitHub, unified" },
];

/**
 * Deliberately understated per design system UX reasoning: no "COMING
 * SOON" badges. Future nodes are dimmed and connected by a dashed line
 * that draws in on scroll (stroke-dashoffset), so "not yet real" is
 * communicated through the visual language itself rather than copy.
 */
export default function Vision() {
  const { ref, inView } = useScrollReveal({ amount: 0.3 });

  return (
    <section id="vision" className="relative py-40 px-5">
      <div className="max-w-[1280px] mx-auto">
        <SectionHeading eyebrow="Vision" title="Where this goes." />

        <div ref={ref} className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-10 md:gap-4 mt-16">
          {ROADMAP.map((step, i) => (
            <div key={step.label} className="flex md:flex-col items-center gap-4 md:gap-0 flex-1 relative">
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={inView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.4, delay: i * 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="flex flex-col items-center text-center"
              >
                <div
                  className={`w-4 h-4 rounded-full ${
                    step.isToday ? "bg-accent-gradient shadow-glow-card" : "border-2 border-white/20 bg-transparent"
                  }`}
                />
                <span className={`mt-4 font-semibold ${step.isToday ? "text-text-primary" : "text-text-secondary"}`}>
                  {step.label}
                </span>
                <span className="mt-1 text-sm text-text-tertiary max-w-[160px]">{step.detail}</span>
              </motion.div>

              {i < ROADMAP.length - 1 && (
                <svg className="hidden md:block absolute top-2 left-1/2 w-full h-1" style={{ marginLeft: "8px" }}>
                  <motion.line
                    x1="0"
                    y1="0"
                    x2="100%"
                    y2="0"
                    stroke="rgba(148,163,184,0.35)"
                    strokeWidth="1.5"
                    strokeDasharray="6 6"
                    initial={{ pathLength: 0 }}
                    animate={inView ? { pathLength: 1 } : { pathLength: 0 }}
                    transition={{ duration: 1.2, delay: i * 0.2 + 0.3, ease: "easeInOut" }}
                  />
                </svg>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
