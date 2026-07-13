import { motion } from "framer-motion";
import { useScrollReveal } from "../../hooks/useScrollReveal";
import SectionHeading from "../ui/SectionHeading";

const NODES = [
  "Recruiter Query",
  "AI Understanding",
  "Knowledge Intelligence",
  "Search Planner",
  "Candidate Intelligence",
  "Explainable Results",
];

const NODE_HEIGHT = 96;

/**
 * The exact 6-node pipeline from the approved design doc, rendered as one
 * continuous SVG so the "pulse of light travels down the connecting line"
 * animation (section 4 of the design system) can be a single stroke-based
 * path animation rather than six separate DOM connectors -- this is what
 * makes the pulse read as one continuous flow instead of six disjointed
 * segments.
 */
export default function HowItThinks() {
  const { ref, inView } = useScrollReveal({ amount: 0.2 });
  const svgHeight = NODES.length * NODE_HEIGHT;
  const centerX = 2;

  return (
    <section id="how-it-thinks" className="relative py-40 px-5">
      <div className="max-w-[900px] mx-auto">
        <SectionHeading
          eyebrow="How AlphaSource Thinks"
          title="A pipeline, not a black box."
          subtitle="Every recommendation can be traced back through exactly these six steps."
        />

        <div ref={ref} className="relative flex justify-center mt-16">
          <svg
            width="4"
            height={svgHeight}
            className="absolute left-1/2 -translate-x-1/2"
            style={{ top: NODE_HEIGHT / 2 }}
          >
            <line
              x1={centerX}
              y1={0}
              x2={centerX}
              y2={svgHeight - NODE_HEIGHT}
              stroke="rgba(255,255,255,0.08)"
              strokeWidth="2"
            />
            {inView && (
              <motion.line
                x1={centerX}
                y1={0}
                x2={centerX}
                y2={svgHeight - NODE_HEIGHT}
                stroke="url(#pulseGradient)"
                strokeWidth="3"
                strokeLinecap="round"
                initial={{ pathLength: 0, opacity: 0.9 }}
                animate={{ pathLength: 1, opacity: [0.9, 0.9, 0] }}
                transition={{ duration: 3.2, ease: "easeInOut", repeat: Infinity, repeatDelay: 1.2 }}
              />
            )}
            <defs>
              <linearGradient id="pulseGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3B82F6" />
                <stop offset="50%" stopColor="#8B5CF6" />
                <stop offset="100%" stopColor="#22D3EE" />
              </linearGradient>
            </defs>
          </svg>

          <div className="flex flex-col items-center relative z-10">
            {NODES.map((node, i) => (
              <PipelineNode key={node} label={node} index={i} inView={inView} isLast={i === NODES.length - 1} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function PipelineNode({ label, index, inView, isLast }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={inView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
      transition={{ duration: 0.4, delay: index * 0.15, ease: [0.16, 1, 0.3, 1] }}
      style={{ height: NODE_HEIGHT }}
      className="flex items-center justify-center"
    >
      <div className="glass-plane-2 rounded-full px-8 py-4 flex items-center gap-3 shadow-glow-card min-w-[280px] justify-center">
        <span className="w-2 h-2 rounded-full bg-accent-gradient" />
        <span className="text-text-primary font-medium text-sm md:text-base">{label}</span>
      </div>
    </motion.div>
  );
}
