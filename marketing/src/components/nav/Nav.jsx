import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Logo from "./Logo";
import GhostButton from "../ui/GhostButton";

const LINKS = [
  { label: "Product", href: "#demo" },
  { label: "Architecture", href: "#architecture" },
  { label: "Vision", href: "#vision" },
  { label: "Enterprise", href: "#enterprise" },
];

/**
 * Glass nav that condenses on scroll (design system section 4: background
 * opacity 0->0.8, blur 0->20px over 300ms). The condensed state is driven
 * by a single boolean derived from scrollY, not per-pixel interpolation --
 * simpler, and the 300ms CSS transition on the container makes the
 * threshold crossing feel smooth regardless.
 */
export default function Nav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 40);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <motion.header
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-base/80 backdrop-blur-2xl border-b border-white/5" : "bg-transparent"
      }`}
    >
      <nav className="max-w-[1280px] mx-auto px-5 md:px-8 flex items-center justify-between h-20">
        <a href="#top" aria-label="AlphaSource AI home">
          <Logo />
        </a>
        <ul className="hidden md:flex items-center gap-10">
          {LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent-cyan rounded-sm"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
        <GhostButton as="a" href="#demo" className="!px-5 !py-2.5 !text-sm">
          Try Live Demo
        </GhostButton>
      </nav>
    </motion.header>
  );
}
