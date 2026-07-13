import { useEffect, useState } from "react";
import { motion } from "framer-motion";

/** Port of frontend/src/App.jsx's computeSummary + SummaryBar, with the
 * count/avg-experience numbers now animated via a simple counter tween
 * (design system's "Numbers: animated counters" micro-interaction) --
 * the underlying aggregation logic is unchanged from the real product. */
function computeSummary(candidates) {
  const count = candidates.length;
  const avgExperience =
    count > 0 ? candidates.reduce((sum, c) => sum + (c.experience || 0), 0) / count : 0;

  const skillFrequency = new Map();
  for (const candidate of candidates) {
    for (const skill of candidate.skills || []) {
      skillFrequency.set(skill, (skillFrequency.get(skill) || 0) + 1);
    }
  }
  const topSkills = [...skillFrequency.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([skill]) => skill);

  return { count, avgExperience, topSkills };
}

function useCountUp(target, duration = 700) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let start;
    let frame;
    function tick(ts) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      setValue(target * progress);
      if (progress < 1) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);
  return value;
}

export default function SummaryBar({ candidates }) {
  if (candidates.length === 0) return null;
  const { count, avgExperience, topSkills } = computeSummary(candidates);
  const animatedCount = useCountUp(count);
  const animatedAvg = useCountUp(avgExperience);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6"
    >
      <div className="glass-plane-2 rounded-xl p-4">
        <p className="text-caption uppercase tracking-[0.08em] text-text-tertiary">Candidates Found</p>
        <p className="mt-1 text-2xl font-semibold text-text-primary">{Math.round(animatedCount)}</p>
      </div>
      <div className="glass-plane-2 rounded-xl p-4">
        <p className="text-caption uppercase tracking-[0.08em] text-text-tertiary">Average Experience</p>
        <p className="mt-1 text-2xl font-semibold text-text-primary">{animatedAvg.toFixed(1)} yrs</p>
      </div>
      <div className="glass-plane-2 rounded-xl p-4">
        <p className="text-caption uppercase tracking-[0.08em] text-text-tertiary">Top Skills</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {topSkills.length > 0 ? (
            topSkills.map((skill) => (
              <span key={skill} className="rounded-full bg-accent-blue/10 border border-accent-blue/20 px-2 py-0.5 text-xs font-medium text-accent-cyan">
                {skill}
              </span>
            ))
          ) : (
            <span className="text-sm text-text-tertiary">—</span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
