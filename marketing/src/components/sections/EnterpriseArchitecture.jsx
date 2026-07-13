import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import SectionHeading from "../ui/SectionHeading";

/**
 * Maps 1:1 to the real, already-built backend modules (see
 * docs/ARCHITECTURE.md / docs/MARKETING_SITE_DESIGN_SYSTEM.md section 7,
 * illustration concept 4): Query Understanding, Knowledge Engine, Search
 * Planner, Candidate Repository. Deliberately not invented/marketing-only
 * boxes -- a technical buyer who knows the real system should recognize
 * it here exactly.
 */
const MODULES = [
  {
    id: "input",
    label: "Recruiter Input",
    x: 40,
    y: 160,
    desc: "A single free-text hiring requirement, in plain English.",
  },
  {
    id: "qu",
    label: "Query Understanding",
    x: 230,
    y: 60,
    desc: "An LLM-backed, provider-agnostic pipeline extracts role and skills into a validated, typed requirement -- with one automatic retry on a malformed response.",
  },
  {
    id: "ke",
    label: "Knowledge Engine",
    x: 230,
    y: 160,
    desc: "A weighted taxonomy graph expands every canonical term into its real-world equivalents, each with a traceable confidence weight.",
  },
  {
    id: "sp",
    label: "Search Planner",
    x: 230,
    y: 260,
    desc: "Combines strict and expanded terms into one executable search plan -- no ranking, no scoring, purely mechanical assembly.",
  },
  {
    id: "cr",
    label: "Candidate Repository",
    x: 480,
    y: 160,
    desc: "A single retrieval interface across every connected candidate source -- built to scale from an in-memory seed set to a full multi-source repository.",
  },
  {
    id: "output",
    label: "Explainable Results",
    x: 660,
    y: 160,
    desc: "Every candidate returned alongside the requirement and search plan that produced it -- so any match can be explained after the fact.",
  },
];

const EDGES = [
  ["input", "qu"],
  ["input", "ke"],
  ["input", "sp"],
  ["qu", "cr"],
  ["ke", "cr"],
  ["sp", "cr"],
  ["cr", "output"],
];

export default function EnterpriseArchitecture() {
  const [active, setActive] = useState(null);
  const activeModule = MODULES.find((m) => m.id === active);

  function isEdgeActive([a, b]) {
    return active && (a === active || b === active);
  }

  return (
    <section id="architecture" className="relative py-40 px-5">
      <div className="max-w-[1280px] mx-auto">
        <SectionHeading
          eyebrow="Enterprise Architecture"
          title="A system, not a script."
          subtitle="Hover any module to see exactly what it does and how it connects."
        />

        <div className="glass-plane-1 rounded-3xl p-6 md:p-10 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8 items-center">
          <svg viewBox="0 0 760 340" className="w-full h-auto">
            {EDGES.map(([a, b]) => {
              const from = MODULES.find((m) => m.id === a);
              const to = MODULES.find((m) => m.id === b);
              const edgeActive = isEdgeActive([a, b]);
              return (
                <line
                  key={`${a}-${b}`}
                  x1={from.x + 70}
                  y1={from.y + 20}
                  x2={to.x}
                  y2={to.y + 20}
                  stroke={edgeActive ? "#8B5CF6" : "rgba(255,255,255,0.12)"}
                  strokeWidth={edgeActive ? 2 : 1}
                  style={{ transition: "stroke 200ms ease-out, stroke-width 200ms ease-out" }}
                />
              );
            })}
            {MODULES.map((mod) => (
              <g
                key={mod.id}
                onMouseEnter={() => setActive(mod.id)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(mod.id)}
                onBlur={() => setActive(null)}
                tabIndex={0}
                role="button"
                aria-label={`${mod.label}: ${mod.desc}`}
                style={{ cursor: "pointer", outline: "none" }}
              >
                <rect
                  x={mod.x}
                  y={mod.y}
                  width={140}
                  height={40}
                  rx={10}
                  fill={active === mod.id ? "rgba(139,92,246,0.18)" : "rgba(255,255,255,0.04)"}
                  stroke={active === mod.id ? "#8B5CF6" : "rgba(255,255,255,0.12)"}
                  style={{ transition: "all 200ms ease-out" }}
                />
                <text
                  x={mod.x + 70}
                  y={mod.y + 24}
                  textAnchor="middle"
                  fontSize="11"
                  fill={active === mod.id ? "#F8FAFC" : "#94A3B8"}
                  style={{ transition: "fill 200ms ease-out" }}
                >
                  {mod.label}
                </text>
              </g>
            ))}
          </svg>

          <div className="min-h-[140px]">
            <AnimatePresence mode="wait">
              {activeModule ? (
                <motion.div
                  key={activeModule.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                  className="glass-plane-2 rounded-xl p-6"
                >
                  <h4 className="font-semibold text-text-primary">{activeModule.label}</h4>
                  <p className="mt-2 text-sm text-text-secondary leading-relaxed">{activeModule.desc}</p>
                </motion.div>
              ) : (
                <motion.p
                  key="hint"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-sm text-text-tertiary p-6"
                >
                  Hover a module in the diagram to learn what it does.
                </motion.p>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
