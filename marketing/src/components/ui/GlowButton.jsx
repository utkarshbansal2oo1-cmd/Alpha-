import { motion } from "framer-motion";

/**
 * The only place full-saturation accent gradient is used as a fill
 * (design system principle: "accent used at low opacity almost
 * everywhere... full-saturation reserved for a handful of focal moments").
 * Primary CTA glow only -- never used for more than one button per
 * viewport (see Hero, which pairs it with GhostButton).
 */
export default function GlowButton({ children, onClick, as: Component = "button", ...props }) {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="relative inline-block group"
    >
      <div className="absolute -inset-1 rounded-full bg-accent-gradient opacity-0 group-hover:opacity-60 blur-xl transition-opacity duration-300" />
      <Component
        onClick={onClick}
        className="relative px-8 py-4 rounded-full bg-accent-gradient text-white font-semibold text-base tracking-tight focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        {...props}
      >
        {children}
      </Component>
    </motion.div>
  );
}
