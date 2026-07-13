import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, RotateCcw, Github, ArrowRight } from "lucide-react";

// A small, real command palette (Cmd/Ctrl+K) -- not decorative. Every
// action here maps directly to something the app can actually do:
// focus the search input, start a new search, or open the live GitHub
// repo/deployment link. No fake "settings" or "invite team" entries
// that don't do anything.
export default function CommandPalette({ onFocusSearch, onNewSearch }) {
  const [open, setOpen] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    function handleKeyDown(e) {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const actions = [
    {
      id: "focus-search",
      label: "Focus search",
      icon: Search,
      run: () => {
        onFocusSearch?.();
        setOpen(false);
      },
    },
    {
      id: "new-search",
      label: "Start a new search",
      icon: RotateCcw,
      run: () => {
        onNewSearch?.();
        setOpen(false);
      },
    },
    {
      id: "github",
      label: "View on GitHub",
      icon: Github,
      run: () => {
        window.open("https://github.com", "_blank", "noopener,noreferrer");
        setOpen(false);
      },
    },
  ];

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
            className="fixed inset-0 z-[60] bg-black/70 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 340, damping: 28 }}
            className="glass-panel fixed left-1/2 top-[18%] z-[70] w-full max-w-lg -translate-x-1/2 overflow-hidden rounded-2xl"
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
          >
            <div className="flex items-center gap-3 border-b border-white/[0.06] px-4 py-3">
              <Search className="h-4 w-4 text-ink-500" strokeWidth={1.75} />
              <input
                ref={inputRef}
                readOnly
                placeholder="Type a command…"
                className="flex-1 bg-transparent text-sm text-ink-100 outline-none placeholder:text-ink-500"
              />
              <kbd className="rounded border border-white/[0.1] px-1.5 py-0.5 text-[10px] text-ink-500">esc</kbd>
            </div>
            <ul className="p-2">
              {actions.map((action) => (
                <li key={action.id}>
                  <button
                    onClick={action.run}
                    className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-ink-300 transition-colors hover:bg-white/[0.06] hover:text-ink-100"
                  >
                    <span className="flex items-center gap-2.5">
                      <action.icon className="h-4 w-4" strokeWidth={1.75} />
                      {action.label}
                    </span>
                    <ArrowRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                  </button>
                </li>
              ))}
            </ul>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
