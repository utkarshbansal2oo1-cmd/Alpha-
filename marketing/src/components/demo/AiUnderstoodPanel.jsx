import { motion } from "framer-motion";

/**
 * Restyled (dark glass) port of frontend/src/App.jsx's AiUnderstood --
 * same data contract (CanonicalJobRequirement: role, skills; location and
 * experience are honestly labeled "Not captured yet" since Query
 * Understanding doesn't extract those fields yet -- see docs/TECH_DEBT.md).
 * Logic is not reinvented, only the visual surface changes.
 */
export default function AiUnderstoodPanel({ requirement }) {
  if (!requirement) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-plane-2 rounded-2xl p-6 mb-8"
    >
      <p className="text-caption uppercase tracking-[0.08em] text-text-tertiary font-medium mb-4">
        AI Understood
      </p>
      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-sm">
        <div>
          <dt className="text-text-tertiary">Role</dt>
          <dd className="mt-1 font-medium text-text-primary">{requirement.role || "—"}</dd>
        </div>
        <div>
          <dt className="text-text-tertiary">Skills</dt>
          <dd className="mt-1 font-medium text-text-primary">
            {requirement.skills?.length > 0 ? requirement.skills.join(", ") : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-text-tertiary">Location</dt>
          <dd className="mt-1 font-medium text-text-tertiary/70">Not captured yet</dd>
        </div>
        <div>
          <dt className="text-text-tertiary">Experience</dt>
          <dd className="mt-1 font-medium text-text-tertiary/70">Not captured yet</dd>
        </div>
      </dl>
    </motion.div>
  );
}
