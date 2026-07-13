import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  MapPin,
  Building2,
  Github,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Code2,
  Activity as ActivityIcon,
  Layers,
  Sparkles,
} from "lucide-react";

// Sprint 22: reorganized into the explicit taxonomy requested -- Profile,
// Evidence, Repositories & Technologies, Activity, Connector metadata,
// GitHub intelligence, Match reasoning. Every value rendered comes
// straight off the Candidate / MatchResult objects the backend already
// returns; nothing here is synthesized copy.

function Section({ icon: Icon, title, children }) {
  return (
    <section>
      <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-ink-500">
        <Icon className="h-3.5 w-3.5" strokeWidth={1.75} />
        {title}
      </h4>
      {children}
    </section>
  );
}

function formatDate(dateStr) {
  if (!dateStr) return null;
  try {
    return new Date(dateStr).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return null;
  }
}

export default function CandidateDrawer({ candidate, match, onClose }) {
  const open = Boolean(candidate);
  const isGithub = candidate?.source === "github";

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            className="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-white/[0.08] bg-void-900/95 backdrop-blur-2xl"
            role="dialog"
            aria-modal="true"
            aria-label={candidate ? `${candidate.name}'s profile` : "Candidate profile"}
          >
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/[0.06] bg-void-900/80 px-6 py-4 backdrop-blur-xl">
              <h2 className="text-lg font-semibold text-ink-100">Candidate profile</h2>
              <button
                onClick={onClose}
                aria-label="Close"
                className="rounded-full p-2 text-ink-500 transition-colors hover:bg-white/[0.06] hover:text-ink-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {candidate && (
              <div className="space-y-7 px-6 py-6">
                {/* --- Profile --- */}
                <Section icon={Sparkles} title="Profile">
                  <div className="flex items-center gap-2">
                    <h3 className="text-2xl font-semibold text-ink-100">{candidate.name}</h3>
                    {isGithub && <Github className="h-4 w-4 text-ink-500" strokeWidth={1.75} />}
                  </div>
                  <p className="mt-1 text-ink-300">
                    {candidate.role !== "Unknown" ? candidate.role : candidate.headline || "Role not specified"}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-500">
                    {candidate.current_company && (
                      <span className="flex items-center gap-1.5">
                        <Building2 className="h-3.5 w-3.5" strokeWidth={1.75} />
                        {candidate.current_company}
                      </span>
                    )}
                    {candidate.location && (
                      <span className="flex items-center gap-1.5">
                        <MapPin className="h-3.5 w-3.5" strokeWidth={1.75} />
                        {candidate.location}
                      </span>
                    )}
                    {candidate.experience > 0 && <span>{candidate.experience} yrs experience</span>}
                  </div>
                  {candidate.public_profile_url && (
                    <a
                      href={candidate.public_profile_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="mt-3 inline-flex items-center gap-1.5 text-sm text-accent-400 hover:text-accent-300"
                    >
                      View public profile <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                  {candidate.summary && <p className="mt-3 text-sm text-ink-300">{candidate.summary}</p>}
                </Section>

                {/* --- Evidence (why this candidate, plain-language) --- */}
                {match?.reasons?.length > 0 && (
                  <Section icon={CheckCircle2} title="Evidence">
                    <ul className="space-y-2">
                      {match.reasons.map((reason, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-ink-300">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-signal-green" strokeWidth={1.75} />
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </Section>
                )}

                {/* --- Repositories & Technologies --- */}
                {(candidate.skills?.length > 0 || candidate.github_languages?.length > 0 || candidate.github_topics?.length > 0) && (
                  <Section icon={Code2} title="Repositories & Technologies">
                    {candidate.skills?.length > 0 && (
                      <div className="mb-3">
                        <p className="mb-1.5 text-xs text-ink-500">Skills</p>
                        <div className="flex flex-wrap gap-2">
                          {candidate.skills.map((skill) => (
                            <span key={skill} className="rounded-full bg-white/[0.06] px-3 py-1 text-sm text-ink-300">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {candidate.github_languages?.length > 0 && (
                      <div className="mb-3">
                        <p className="mb-1.5 text-xs text-ink-500">Languages (from real repos)</p>
                        <div className="flex flex-wrap gap-2">
                          {candidate.github_languages.map((lang) => (
                            <span key={lang} className="rounded-full bg-accent-500/10 px-3 py-1 text-sm text-accent-300">
                              {lang}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {candidate.github_topics?.length > 0 && (
                      <div>
                        <p className="mb-1.5 text-xs text-ink-500">Repo topics</p>
                        <div className="flex flex-wrap gap-2">
                          {candidate.github_topics.map((topic) => (
                            <span key={topic} className="rounded-full bg-white/[0.04] px-3 py-1 text-xs text-ink-500">
                              {topic}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </Section>
                )}

                {/* --- Activity --- */}
                {isGithub && (candidate.github_last_activity || candidate.github_repositories_analyzed != null) && (
                  <Section icon={ActivityIcon} title="Activity">
                    <dl className="grid grid-cols-2 gap-3 text-sm">
                      {candidate.github_last_activity && (
                        <div>
                          <dt className="text-xs text-ink-500">Last active</dt>
                          <dd className="text-ink-100">{formatDate(candidate.github_last_activity)}</dd>
                        </div>
                      )}
                      {candidate.github_repositories_analyzed != null && (
                        <div>
                          <dt className="text-xs text-ink-500">Repositories analyzed</dt>
                          <dd className="text-ink-100">{candidate.github_repositories_analyzed}</dd>
                        </div>
                      )}
                      {candidate.github_activity_score != null && (
                        <div>
                          <dt className="text-xs text-ink-500">Activity score</dt>
                          <dd className="text-ink-100">{Math.round(candidate.github_activity_score)}/100</dd>
                        </div>
                      )}
                    </dl>
                  </Section>
                )}

                {/* --- Connector metadata --- */}
                {(candidate.source || candidate.capture_sources?.length > 0) && (
                  <Section icon={Layers} title="Connector metadata">
                    <dl className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <dt className="text-ink-500">Source</dt>
                        <dd className="capitalize text-ink-100">{candidate.source?.replace(/_/g, " ")}</dd>
                      </div>
                      {candidate.version != null && (
                        <div className="flex justify-between">
                          <dt className="text-ink-500">Record version</dt>
                          <dd className="text-ink-100">v{candidate.version}</dd>
                        </div>
                      )}
                      {candidate.capture_sources?.length > 0 && (
                        <div className="flex justify-between">
                          <dt className="text-ink-500">Capture events</dt>
                          <dd className="text-ink-100">{candidate.capture_sources.length}</dd>
                        </div>
                      )}
                      {candidate.health_score != null && (
                        <div className="flex justify-between">
                          <dt className="text-ink-500">Profile health</dt>
                          <dd className="text-ink-100">{Math.round(candidate.health_score)}/100</dd>
                        </div>
                      )}
                    </dl>
                  </Section>
                )}

                {/* --- GitHub intelligence --- */}
                {isGithub && (
                  <Section icon={Github} title="GitHub intelligence">
                    <dl className="grid grid-cols-2 gap-3 text-sm">
                      {candidate.github_quality_score != null && (
                        <div>
                          <dt className="text-xs text-ink-500">Quality score</dt>
                          <dd className="text-ink-100">{Math.round(candidate.github_quality_score)}/100</dd>
                        </div>
                      )}
                      {candidate.github_profile_completeness != null && (
                        <div>
                          <dt className="text-xs text-ink-500">Profile completeness</dt>
                          <dd className="text-ink-100">{Math.round(candidate.github_profile_completeness)}%</dd>
                        </div>
                      )}
                      {candidate.github_organizations?.length > 0 && (
                        <div className="col-span-2">
                          <dt className="text-xs text-ink-500">Organizations</dt>
                          <dd className="text-ink-100">{candidate.github_organizations.join(", ")}</dd>
                        </div>
                      )}
                      {candidate.github_skills_inferred?.length > 0 && (
                        <div className="col-span-2">
                          <dt className="text-xs text-ink-500">Skills inferred from evidence</dt>
                          <dd className="text-ink-100">{candidate.github_skills_inferred.join(", ")}</dd>
                        </div>
                      )}
                    </dl>
                  </Section>
                )}

                {/* --- Match reasoning --- */}
                {match && (
                  <Section icon={Sparkles} title="Match reasoning">
                    <p className="mb-3 text-sm text-ink-500">
                      Overall match: <span className="font-medium text-ink-100">{Math.round(match.overall_score)}/100</span>
                    </p>
                    <div className="space-y-2">
                      {Object.entries(match.component_scores || {}).map(([dimension, score]) => (
                        <div key={dimension} className="flex items-center gap-3">
                          <span className="w-28 shrink-0 text-xs capitalize text-ink-500">
                            {dimension.replace(/_/g, " ")}
                          </span>
                          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.06]">
                            <div
                              className="h-full rounded-full bg-accent-500"
                              style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
                            />
                          </div>
                          <span className="w-8 shrink-0 text-right text-xs tabular-nums text-ink-300">
                            {Math.round(score)}
                          </span>
                        </div>
                      ))}
                    </div>
                    {match.missing_fields?.length > 0 && (
                      <ul className="mt-4 space-y-1.5">
                        {match.missing_fields.map((field, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-ink-500">
                            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-signal-amber" strokeWidth={1.75} />
                            Not confirmed: {field.replace(/_/g, " ")}
                          </li>
                        ))}
                      </ul>
                    )}
                  </Section>
                )}
              </div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
