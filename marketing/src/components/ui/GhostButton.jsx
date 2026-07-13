import { motion } from "framer-motion";

export default function GhostButton({ children, onClick, as: Component = "button", className = "", ...props }) {
  return (
    <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} transition={{ duration: 0.2 }}>
      <Component
        onClick={onClick}
        className={`px-8 py-4 rounded-full border border-white/15 text-text-primary font-medium text-base bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/25 transition-colors duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-cyan ${className}`}
        {...props}
      >
        {children}
      </Component>
    </motion.div>
  );
}
