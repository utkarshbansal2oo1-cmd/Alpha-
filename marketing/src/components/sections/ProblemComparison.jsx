import { motion } from "framer-motion";
import SectionHeading from "../ui/SectionHeading";
import { useScrollReveal } from "../../hooks/useScrollReveal";

const TRADITIONAL_STEPS = [
  "2,000 Resumes",
  "100 Interviews",
  "20 Shortlisted",
  "1 Hire",
];

const ALPHASOURCE_STEPS = [
  "Recruiter Intent",
  "AI Understanding",
  "Knowledge Intelligence",
  "Explainable Results",
];

/**
 * The core visual argument of the page (design system section 2 / UX
 * reasoning): both chains animate on scroll-into-view in parallel, but the
 * AlphaSource chain uses fewer nodes, a lighter spring (fast ease-out) and
 * finishes noticeably before the Traditional chain (heavier spring,
 * overshoot, slower stagger). No copy claims "we're faster" -- the
 * animation timing itself is the argument.
 */
function Chain({ steps, variant }) {
  const isTraditional = variant === "traditional";

  return (
    <div className="flex flex-col items-center gap-0">
      {steps.map((step, i) => (
        <div key={step} className="flex flex-col items-center">
          <ChainNode step={step} index={i} isTraditional={isTraditional} />
          {i < steps.length - 1 && (
            <ChainConnector index={i} isTraditional={isTraditional} />
          )}
        </div>
      ))}
    </div>
  );
}

function ChainNode({ step, index, isTraditional }) {
  const { ref, inView } = useScrollReveal({ amount: 0.4 });

  const transition = isTraditional
    ? { type: "spring", damping: 8, stiffness: 90, delay: index * 0.35 }
    : { duration: 0.25, ease: "easeOut", delay: index * 0.15 };

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: -10 }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: -10 }}
      transition={transition}
      className={`w-64 text-center py-4 px-6 rounded-xl border ${
        isTraditional
          ? "border-white/8 bg-white/[0.02] text-text-tertiary"
          : "glass-plane-2 text-text-primary shadow-glow-card"
      }`}
    >
      <span className={isTraditional ? "text-sm" : "text-sm font-medium"}>{step}</span>
    </motion.div>
  );
}

function ChainConnector({ index, isTraditional }) {
  const { ref, inView } = useScrollReveal({ amount: 0.4 });
  return (
    <motion.div
      ref={ref}
      initial={{ scaleY: 0, opacity: 0 }}
      animate={inView ? { scaleY: 1, opacity: 1 } : { scaleY: 0, opacity: 0 }}
      transition={{
        duration: isTraditional ? 0.5 : 0.25,
        delay: index * (isTraditional ? 0.35 : 0.15) + 0.15,
        ease: "easeOut",
      }}
      style={{ transformOrigin: "top" }}
      className={`w-px h-8 ${isTraditional ? "bg-white/10" : "bg-gradient-to-b from-accent-blue to-accent-purple"}`}
    />
  );
}

export default function ProblemComparison() {
  return (
    <section id="problem" className="relative py-40 px-5">
      <div className="max-w-[1280px] mx-auto">
        <SectionHeading
          eyebrow="The Problem"
          title="The old way costs you the best candidates."
          subtitle="Every extra hop between a job requirement and a hire is a candidate you lose to a faster competitor."
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-16 md:gap-8 justify-items-center mt-20">
          <div className="flex flex-col items-center gap-6">
            <span className="text-caption uppercase tracking-[0.08em] text-text-tertiary font-medium">
              Traditional Hiring
            </span>
            <Chain steps={TRADITIONAL_STEPS} variant="traditional" />
          </div>
          <div className="flex flex-col items-center gap-6">
            <span className="text-caption uppercase tracking-[0.08em] text-accent-cyan font-medium">
              AlphaSource
            </span>
            <Chain steps={ALPHASOURCE_STEPS} variant="alphasource" />
          </div>
        </div>
      </div>
    </section>
  );
}
