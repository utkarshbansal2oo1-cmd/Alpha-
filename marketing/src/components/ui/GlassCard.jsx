import { motion } from "framer-motion";
import { useCursorGlow } from "../../hooks/useCursorGlow";

/**
 * Plane 2 card primitive (glassmorphism.md section 1.3). Used by
 * FeatureShowcase and anywhere else a bordered glass surface with a
 * cursor-tracked glow and hover-lift is needed, so that interaction stays
 * consistent site-wide rather than re-implemented per section.
 */
export default function GlassCard({ children, className = "" }) {
  const { onMouseMove } = useCursorGlow();
  return (
    <motion.div
      onMouseMove={onMouseMove}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={`cursor-glow glass-plane-2 rounded-2xl p-8 hover:border-white/20 transition-colors duration-200 ${className}`}
    >
      {children}
    </motion.div>
  );
}
