import { motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import NeuralNetworkBackground from "../animations/NeuralNetworkBackground";
import GlowButton from "../ui/GlowButton";
import GhostButton from "../ui/GhostButton";

const HEADLINE_LINE_1 = "Stop Searching.";
const HEADLINE_LINE_2 = "Start Hiring Intelligently.";

/** Staggered word-reveal per design system: 60ms stagger, 600ms ease-out
 * per word, y:20->0 opacity:0->1. Split by word (not by character) --
 * character-level reveal on an 88px headline reads as gimmicky, word-level
 * reads as deliberate. */
function AnimatedHeadline() {
  const words1 = HEADLINE_LINE_1.split(" ");
  const words2 = HEADLINE_LINE_2.split(" ");
  const allWords = [...words1, ...words2];

  return (
    <h1 className="text-hero-mobile md:text-hero-desktop font-bold text-text-primary text-center">
      <span className="block">
        {words1.map((word, i) => (
          <Word key={`l1-${i}`} word={word} index={i} />
        ))}
      </span>
      <span className="block accent-text">
        {words2.map((word, i) => (
          <Word key={`l2-${i}`} word={word} index={words1.length + i} />
        ))}
      </span>
    </h1>
  );
}

function Word({ word, index }) {
  return (
    <motion.span
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: index * 0.06, ease: [0.16, 1, 0.3, 1] }}
      className="inline-block mr-[0.28em]"
    >
      {word}
    </motion.span>
  );
}

export default function Hero() {
  return (
    <section
      id="top"
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden px-5"
    >
      {/* Parallax note: this background layer is the only place parallax
          is used (design system: "hero background moves ~30% slower than
          foreground"), implemented via a slower-than-scroll fixed position
          rather than JS scroll listeners, to stay off the main thread. */}
      <div className="absolute inset-0" style={{ transform: "translateZ(0)" }}>
        <NeuralNetworkBackground />
        <div className="absolute inset-0 bg-gradient-to-b from-base/0 via-base/40 to-base pointer-events-none" />
      </div>

      <div className="relative z-10 max-w-4xl mx-auto flex flex-col items-center text-center">
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="text-caption uppercase tracking-[0.08em] text-text-tertiary font-medium mb-6"
        >
          AlphaSource AI &middot; Powered by AlphaRecrewt
        </motion.span>

        <AnimatedHeadline />

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mt-8 text-body-large text-text-secondary font-normal max-w-xl"
        >
          Describe the candidate you need. AI understands your intent, finds
          the best talent, and explains every recommendation.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="mt-12 flex flex-col sm:flex-row items-center gap-4"
        >
          <GlowButton as="a" href="#demo">
            Try Live Demo
          </GlowButton>
          <GhostButton as="a" href="#how-it-thinks">
            Watch Architecture
          </GhostButton>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.6, duration: 0.6 }}
        className="absolute bottom-10 left-1/2 -translate-x-1/2 z-10"
      >
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <ChevronDown className="text-text-tertiary" size={24} />
        </motion.div>
      </motion.div>
    </section>
  );
}
