import { motion } from "framer-motion";
import { useScrollReveal, staggerContainer } from "../../hooks/useScrollReveal";
import SectionHeading from "../ui/SectionHeading";

const STEPS = [
  { label: "Step 1", title: "Recruiter types", detail: "A single sentence, in plain English." },
  { label: "Step 2", title: "AI understands", detail: "Role, skills, and intent are extracted." },
  { label: "Step 3", title: "Knowledge expands", detail: "Related skills and roles are surfaced." },
  { label: "Step 4", title: "Search executes", detail: "The expanded plan is run against every source." },
  { label: "Step 5", title: "Explainable recommendations", detail: "Every match comes with its reasoning." },
];

/**
 * "Each node lights up sequentially" per brief -- implemented as a single
 * scroll-triggered stagger (not per-node individual scroll triggers, which
 * would fire out of order on fast scrolls). staggerChildren guarantees
 * strict left-to-right sequencing regardless of scroll speed.
 */
export default function ProductJourney() {
  const { ref, inView } = useScrollReveal({ amount: 0.25 });

  return (
    <section className="relative py-40 px-5">
      <div className="max-w-[1280px] mx-auto">
        <SectionHeading
          eyebrow="Interactive Product Journey"
          title="From a sentence to a shortlist."
        />
        <motion.div
          ref={ref}
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          variants={staggerContainer(0.25)}
          className="grid grid-cols-1 md:grid-cols-5 gap-6 md:gap-4 mt-16"
        >
          {STEPS.map((step, i) => (
            <div key={step.title} className="flex md:flex-col items-center gap-4 md:gap-0">
              <motion.div
                variants={{
                  hidden: { opacity: 0, scale: 0.85 },
                  visible: {
                    opacity: 1,
                    scale: 1,
                    transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] },
                  },
                }}
                className="flex flex-col items-center text-center md:w-full"
              >
                <div className="relative w-14 h-14 rounded-full glass-plane-2 flex items-center justify-center shadow-glow-card">
                  <span className="accent-text font-bold text-lg">{i + 1}</span>
                </div>
                <span className="mt-4 text-caption uppercase tracking-[0.08em] text-text-tertiary">
                  {step.label}
                </span>
                <h3 className="mt-2 font-semibold text-text-primary">{step.title}</h3>
                <p className="mt-1 text-sm text-text-secondary max-w-[180px]">{step.detail}</p>
              </motion.div>
              {i < STEPS.length - 1 && (
                <motion.div
                  variants={{
                    hidden: { scaleX: 0, opacity: 0 },
                    visible: { scaleX: 1, opacity: 1, transition: { duration: 0.35 } },
                  }}
                  style={{ transformOrigin: "left" }}
                  className="hidden md:block h-px flex-1 bg-gradient-to-r from-accent-blue/40 to-accent-purple/40 mt-7"
                />
              )}
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
