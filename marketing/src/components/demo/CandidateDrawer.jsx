import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, MapPin, Briefcase, GraduationCap, Award, Languages, FileText, Activity, Clock } from "lucide-react";
import WhyMatchedTag, { computeWhyMatched } from "./WhyMatchedTag";

/**
 * Sprint 6, Task 4: candidate profile side panel. Reads rich fields
 * (education, timeline, projects, certifications, languages) when present
 * -- true for every Guided Demo Mode candidate (src/data/candidates.js) --
 * and degrades honestly (an explicit "Not available for this candidate"
 * note, not a fabricated placeholder) when a candidate came from the real
 * backend, whose Candidate model only carries id/name/role/experience/
 * skills/location/current_company/source. This mirrors the project's
 * established pattern of labeling ungathered data honestly rather than
 * inventing it (see frontend/src/App.jsx's "Not captured yet" for
 * location/experience in AI Understood).
 *
 * Sprint 14 addition: a "Candidate Health" section rendered whenever the
 * candidate carries `health_score` -- true for every candidate returned by
 * the real backend (Live Pipeline mode) after the Candidate Intelligence
 * Lifecycle wiring in InMemoryCandidateRepository, since seed data and
 * captured candidates both get a health score computed on write. Guided
 * Demo Mode's locally-generated fictional candidates never carry this
 * field, so the section simply doesn't render for them -- same
 * data-source-honesty pattern as the rest of this file, not a bug.
 */
export default function CandidateDrawer({ candidate, searchPlan, onClose }) {
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = candidate ? "hidden" : "";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [candidate, onClose]);

  const hasRichProfile = Boolean(candidate?.education || candidate?.timeline);
  const hasHealthData = typeof candidate?.health_score === "number";
  const whyMatched = candidate ? computeWhyMatched(candidate, searchPlan) : [];

  return (
    <AnimatePresence>
      {candidate && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]"
            aria-hidden="true"
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={`${candidate.name} profile`}
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="fixed top-0 right-0 h-full w-full sm:w-[440px] z-[70] glass-plane-3 !rounded-none sm:!rounded-l-3xl overflow-y-auto"
          >
            <div className="p-6 md:p-8">
              <button
                onClick={onClose}
                aria-label="Close candidate profile"
                className="absolute top-6 right-6 w-9 h-9 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-cyan"
              >
                <X size={16} className="text-text-secondary" />
              </button>

              <div className="pr-12">
                <div className="flex items-center gap-3 flex-wrap">
                  <h2 className="text-2xl font-bold text-text-primary">{candidate.name}</h2>
                  {hasHealthData && <HealthBadge score={candidate.health_score} />}
                </div>
                <p className="mt-1 text-text-secondary">{candidate.role}</p>
                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-text-tertiary">
                  <span className="flex items-center gap-1.5">
                    <Briefcase size={14} /> {candidate.current_company}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <MapPin size={14} /> {candidate.location}
                  </span>
                  <span>{candidate.experience} yrs experience</span>
                </div>
                {candidate.notice_period && (
                  <span className="inline-block mt-3 text-xs font-medium px-2.5 py-1 rounded-full bg-accent-blue/10 border border-accent-blue/20 text-accent-cyan">
                    {candidate.notice_period}
                  </span>
                )}
              </div>

              {whyMatched.length > 0 && (
                <div className="mt-6">
                  <WhyMatchedTag candidate={candidate} searchPlan={searchPlan} />
                </div>
              )}

              {hasHealthData && (
                <Section title="Candidate Health" icon={Activity}>
                  <div className="space-y-3">
                    {Object.entries(candidate.section_confidence || {}).map(([section, confidence]) => (
                      <ConfidenceBar key={section} section={section} confidence={confidence} />
                    ))}
                    {candidate.version > 1 && (
                      <p className="text-xs text-text-tertiary">
                        Profile version {candidate.version} &middot; enriched from{" "}
                        {candidate.capture_sources?.length || 1} source
                        {(candidate.capture_sources?.length || 1) === 1 ? "" : "s"}
                      </p>
                    )}
                  </div>

                  {candidate.evidence_history?.length > 0 && (
                    <div className="mt-4">
                      <p className="flex items-center gap-1.5 text-xs font-medium text-text-tertiary uppercase tracking-[0.06em] mb-2">
                        <Clock size={12} /> Recent evidence
                      </p>
                      <ul className="space-y-2">
                        {[...candidate.evidence_history]
                          .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                          .slice(0, 4)
                          .map((event) => (
                            <li key={event.event_id} className="text-xs text-text-secondary leading-relaxed border-l-2 border-white/10 pl-3">
                              <span className="text-text-primary font-medium">{event.field}</span>{" "}
                              {event.change_type} from <span className="text-accent-cyan">{event.source_type}</span>
                              {" "}&middot; {Math.round(event.confidence * 100)}% confidence
                              <div className="text-text-tertiary">{event.reason}</div>
                            </li>
                          ))}
                      </ul>
                    </div>
                  )}
                </Section>
              )}

              <Section title="Skills">
                <div className="flex flex-wrap gap-2">
                  {candidate.skills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-full bg-accent-blue/10 border border-accent-blue/20 px-2.5 py-1 text-xs font-medium text-accent-cyan"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </Section>

              {hasRichProfile ? (
                <>
                  <Section title="Experience Timeline" icon={Briefcase}>
                    <ol className="relative border-l border-white/10 pl-4 space-y-4">
                      {candidate.timeline.map((role, i) => (
                        <li key={i} className="relative">
                          <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-accent-gradient" />
                          <p className="text-sm font-medium text-text-primary">{role.title}</p>
                          <p className="text-xs text-text-tertiary">
                            {role.company} &middot; {role.start}–{role.current ? "Present" : role.end}
                          </p>
                        </li>
                      ))}
                    </ol>
                  </Section>

                  <Section title="Education" icon={GraduationCap}>
                    <p className="text-sm text-text-primary font-medium">{candidate.education.degree}</p>
                    <p className="text-sm text-text-secondary">
                      {candidate.education.school} &middot; {candidate.education.year}
                    </p>
                  </Section>

                  {candidate.projects?.length > 0 && (
                    <Section title="Projects">
                      <ul className="space-y-2">
                        {candidate.projects.map((p, i) => (
                          <li key={i} className="text-sm text-text-secondary leading-relaxed flex gap-2">
                            <span className="text-accent-cyan">&bull;</span>
                            <span>{p}</span>
                          </li>
                        ))}
                      </ul>
                    </Section>
                  )}

                  {candidate.certifications?.length > 0 && (
                    <Section title="Certifications" icon={Award}>
                      <div className="flex flex-wrap gap-2">
                        {candidate.certifications.map((c) => (
                          <span key={c} className="rounded-lg bg-white/5 border border-white/10 px-2.5 py-1 text-xs text-text-secondary">
                            {c}
                          </span>
                        ))}
                      </div>
                    </Section>
                  )}

                  {candidate.languages?.length > 0 && (
                    <Section title="Languages" icon={Languages}>
                      <p className="text-sm text-text-secondary">{candidate.languages.join(", ")}</p>
                    </Section>
                  )}

                  <Section title="Resume Preview" icon={FileText}>
                    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-text-tertiary italic">
                      Full resume preview is available inside the AlphaSource recruiter
                      application after shortlisting -- this panel shows the structured
                      profile data used to generate the match.
                    </div>
                  </Section>
                </>
              ) : (
                <Section title="Full Profile">
                  <p className="text-sm text-text-tertiary italic">
                    Experience timeline, education, projects, certifications, and resume
                    preview are not available for candidates sourced from the live
                    connected pipeline yet -- only role, skills, experience, and company
                    are captured today. This is a data-source honesty note, not a bug.
                  </p>
                </Section>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function Section({ title, icon: Icon, children }) {
  return (
    <div className="mt-8">
      <h3 className="flex items-center gap-2 text-caption uppercase tracking-[0.08em] text-text-tertiary font-medium mb-3">
        {Icon && <Icon size={13} />}
        {title}
      </h3>
      {children}
    </div>
  );
}

/** Score badge for the drawer header -- color reflects the same
 * three-tier read a recruiter would give it at a glance: red under 40
 * ("barely usable, enrich before outreach"), amber 40-70 ("workable,
 * gaps remain"), green 70+ ("solid profile"). Thresholds are a product
 * judgment call, not derived from the backend -- documented here since
 * they live only in this component. */
function HealthBadge({ score }) {
  const tier = score >= 70 ? "high" : score >= 40 ? "mid" : "low";
  const styles = {
    high: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    mid: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    low: "bg-rose-500/10 border-rose-500/30 text-rose-400",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${styles[tier]}`}>
      <Activity size={12} /> {Math.round(score)} health
    </span>
  );
}

function ConfidenceBar({ section, confidence }) {
  const pct = Math.round(confidence * 100);
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-text-secondary capitalize">{section}</span>
        <span className="text-text-tertiary">{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div className="h-full bg-accent-gradient" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
