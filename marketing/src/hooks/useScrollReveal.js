import { useRef } from "react";
import { useInView } from "framer-motion";

/**
 * Standardizes the "fade + translate-y on scroll into view, no exit
 * animation" rule from the animation plan (docs/MARKETING_SITE_DESIGN_SYSTEM.md
 * section 4) so every section uses identical timing/easing instead of each
 * component inventing its own variant.
 */
export function useScrollReveal({ amount = 0.3, once = true } = {}) {
  const ref = useRef(null);
  const inView = useInView(ref, { amount, once });
  return { ref, inView };
}

export const revealVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] },
  },
};

export const staggerContainer = (staggerChildren = 0.1, delayChildren = 0) => ({
  hidden: {},
  visible: {
    transition: { staggerChildren, delayChildren },
  },
});
