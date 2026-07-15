import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Github, Loader2, ShieldAlert, X } from "lucide-react";
import { configureGithub, disconnectGithub, SearchError } from "../api";

// Sprint 37: the complete recruiter-facing GitHub connection flow --
// Connect button (rendered by the caller, see App.jsx), PAT input,
// Verify+Save (one call, see api.js#configureGithub -- the backend
// verifies against the real GitHub API before persisting anything),
// success state, error state, Reconnect (re-showing the input even when
// already connected), and Disconnect. This component owns none of the
// "is GitHub connected" state itself -- it's handed `status` (the
// `github` key from GET /integrations/status) and calls `onStatusChange`
// with the fresh status after any action so the parent (App.jsx) stays
// the single source of truth.
export default function GithubConnectModal({ open, onClose, status, onStatusChange }) {
  const [token, setToken] = useState("");
  const [mode, setMode] = useState("view"); // "view" | "editing"
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [justConnected, setJustConnected] = useState(null); // { verified_username, verified_scopes } | null

  useEffect(() => {
    if (open) {
      setMode(status?.configured ? "view" : "editing");
      setToken("");
      setError(null);
      setJustConnected(null);
    }
  }, [open, status?.configured]);

  if (!open) return null;

  const handleVerifyAndSave = async (e) => {
    e.preventDefault();
    if (!token.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await configureGithub(token.trim());
      setJustConnected(result);
      setToken("");
      setMode("view");
      onStatusChange?.({
        configured: true,
        status: "connected",
        verified_username: result.verified_username,
        verified_scopes: result.verified_scopes,
      });
    } catch (err) {
      setError(err instanceof SearchError ? err.message : String(err?.message || err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDisconnect = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await disconnectGithub();
      setJustConnected(null);
      setMode("editing");
      onStatusChange?.({ configured: false, status: "unconfigured" });
    } catch (err) {
      setError(err instanceof SearchError ? err.message : String(err?.message || err));
    } finally {
      setSubmitting(false);
    }
  };

  const isConnected = status?.configured && status?.status === "connected";

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, y: 12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 12, scale: 0.98 }}
          transition={{ duration: 0.2 }}
          className="glass-panel w-full max-w-md rounded-2xl p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.06]">
                <Github className="h-4 w-4 text-ink-100" strokeWidth={1.75} />
              </div>
              <div>
                <p className="text-sm font-semibold text-ink-100">GitHub connection</p>
                <p className="text-xs text-ink-500">Live candidate discovery from GitHub</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="rounded-full p-1 text-ink-500 transition-colors hover:bg-white/[0.06] hover:text-ink-100"
            >
              <X className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>

          <div className="mt-5">
            {mode === "view" && isConnected && (
              <div className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-4">
                <div className="flex items-center gap-2 text-signal-green">
                  <CheckCircle2 className="h-4 w-4" strokeWidth={1.75} />
                  <span className="text-sm font-medium">Connected</span>
                </div>
                {status.verified_username && (
                  <p className="mt-2 text-sm text-ink-300">
                    Authenticated as <span className="font-medium text-ink-100">@{status.verified_username}</span>
                  </p>
                )}
                {status.verified_scopes?.length > 0 && (
                  <p className="mt-1 text-xs text-ink-500">Scopes: {status.verified_scopes.join(", ")}</p>
                )}
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => setMode("editing")}
                    className="rounded-full border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs font-medium text-ink-300 transition-colors hover:bg-white/[0.08] hover:text-ink-100"
                  >
                    Reconnect
                  </button>
                  <button
                    onClick={handleDisconnect}
                    disabled={submitting}
                    className="rounded-full border border-signal-red/30 bg-signal-red/10 px-3.5 py-1.5 text-xs font-medium text-signal-red transition-colors hover:bg-signal-red/20 disabled:opacity-50"
                  >
                    {submitting ? "Disconnecting…" : "Disconnect"}
                  </button>
                </div>
              </div>
            )}

            {mode === "editing" && (
              <form onSubmit={handleVerifyAndSave}>
                <label className="text-xs font-medium text-ink-400">Personal Access Token</label>
                <input
                  type="password"
                  autoFocus
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="ghp_..."
                  className="mt-1.5 w-full rounded-lg border border-white/[0.08] bg-white/[0.03] px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:border-accent-500/50 focus:outline-none"
                />
                <p className="mt-1.5 text-xs text-ink-600">
                  Generate one from GitHub Settings → Developer settings → Personal access tokens. Verified live
                  before it's saved -- nothing is stored if it doesn't authenticate.
                </p>

                {error && (
                  <div className="mt-3 flex items-start gap-2 rounded-lg border border-signal-red/30 bg-signal-red/10 p-3">
                    <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-signal-red" strokeWidth={1.75} />
                    <p className="text-xs text-signal-red">{error}</p>
                  </div>
                )}

                <div className="mt-4 flex gap-2">
                  <button
                    type="submit"
                    disabled={submitting || !token.trim()}
                    className="flex items-center gap-1.5 rounded-full bg-accent-500 px-4 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent-600 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={2} />}
                    {submitting ? "Verifying…" : "Verify & Connect"}
                  </button>
                  {isConnected && (
                    <button
                      type="button"
                      onClick={() => {
                        setMode("view");
                        setError(null);
                      }}
                      className="rounded-full border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs font-medium text-ink-300 transition-colors hover:bg-white/[0.08] hover:text-ink-100"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </form>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
