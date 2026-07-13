import { motion } from "framer-motion";
import { Brain, Network, Sparkles, ShieldCheck, Layers, Link2 } from "lucide-react";
import SectionHeading from "../ui/SectionHeading";
import GlassCard from "../ui/GlassCard";
import { useScrollReveal, staggerContainer } from "../../hooks/useScrollReveal";

const FEATURES = [
  {
    icon: Brain,
    title: "AI Query Understanding",
    desc: "Recruiters describe intent in plain English. The system extracts role and skills with a validated, retried LLM pipeline -- not keyword matching.",
  },
  {
    icon: Network,
    title: "Knowledge Intelligence",
    desc: "A weighted taxonomy graph expands every requirement into its real-world equivalents -- AWS becomes EC2, Lambda, and S3, each with a traceable confidence weight.",
  },
  {
    icon: Sparkles,
    title: "Explainable AI",
    desc: "Every candidate ships with the exact reasoning behind the match -- which strict term, which skill, which expansion. No black-box scores.",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise Ready",
    desc: "Provider-agnostic AI layer, typed contracts end-to-end, and a tested pipeline built for the reliability enterprise deployments require.",
  },
  {
    icon: Layers,
    title: "Multi-source Intelligence",
    desc: "One retrieval interface across every connected candidate source -- built to scale from a single seed dataset to a full multi-source repository.",
  },
  {
    icon: Link2,
    title: "AlphaRecrewt Integration",
    desc: "Shortlist directly into AlphaRecrewt for assessments and interviews -- search and hiring, in one continuous flow.",
  },
];

export default function FeatureShowcase() {
  const { ref, inView } = useScrollReveal({ amount: 0.15 });

  return (
    <section id="enterprise" className="relative py-40 px-5">
      <div className="max-w-[1280px] mx-auto">
        <SectionHeading
          eyebrow="Enterprise Capabilities"
          title="Built for how enterprises actually hire."
        />
        <motion.div
          ref={ref}
          initial="hidden"
          animate={inView ? "visible" : "hidden"}
          variants={staggerContainer(0.1)}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {FEATURES.map((feature) => (
            <motion.div
              key={feature.title}
              variants={{
                hidden: { opacity: 0, y: 24 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
              }}
            >
              <GlassCard className="h-full">
                <feature.icon className="text-accent-cyan" size={28} strokeWidth={1.5} />
                <h3 className="mt-5 text-lg font-semibold text-text-primary">{feature.title}</h3>
                <p className="mt-3 text-sm text-text-secondary leading-relaxed">{feature.desc}</p>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
