import { motion } from "framer-motion";
import { useScrollReveal, revealVariants } from "../../hooks/useScrollReveal";

/**
 * Every section (Problem, Pipeline, Demo, Features, Architecture, Vision)
 * uses this exact heading treatment -- one of the design system's core
 * rules is that repeated primitives (not per-section bespoke headings) are
 * what keeps a multi-section page from feeling like assembled templates.
 */
export default function SectionHeading({ eyebrow, title, subtitle, align = "center" }) {
  const { ref, inView } = useScrollReveal();
  const alignClass = align === "center" ? "text-center items-center" : "text-left items-start";

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={inView ? "visible" : "hidden"}
      variants={revealVariants}
      className={`flex flex-col ${alignClass} max-w-3xl mx-auto mb-16`}
    >
      {eyebrow && (
        <span className="text-caption uppercase tracking-[0.08em] text-text-tertiary font-medium mb-4">
          {eyebrow}
        </span>
      )}
      <h2 className="text-section-mobile md:text-section-desktop font-bold text-text-primary">
        {title}
      </h2>
      {subtitle && (
        <p className="mt-6 text-body-large text-text-secondary font-normal max-w-2xl">
          {subtitle}
        </p>
      )}
    </motion.div>
  );
}
