import { forwardRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Search } from "lucide-react";

// The homepage IS this component's container -- there is no marketing
// copy above it, no example chips, no "try one of these roles" list.
// A recruiter types their own real requirement, in their own words, and
// that string is sent verbatim to Query Understanding. Nothing here
// implies a closed set of supported roles or skills.
const SearchBar = forwardRef(function SearchBar({ onSearch, disabled, initialValue = "" }, ref) {
  const [value, setValue] = useState(initialValue);

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSearch(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-3xl">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="glass-input relative flex items-center gap-3 rounded-2xl px-5 py-4 sm:px-6 sm:py-5 shadow-glass focus-within:shadow-glow transition-shadow duration-300"
      >
        <Search className="h-5 w-5 shrink-0 text-ink-500" strokeWidth={1.75} />
        <input
          ref={ref}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder="Search any role, technology, skill or hiring requirement..."
          aria-label="Hiring requirement"
          className="flex-1 bg-transparent text-base sm:text-lg text-ink-100 placeholder:text-ink-500/70 outline-none disabled:opacity-50"
          autoFocus
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Search"
          className="flex h-10 w-10 sm:h-11 sm:w-11 shrink-0 items-center justify-center rounded-xl bg-accent-500 text-white transition-all duration-200 hover:bg-accent-400 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-accent-500"
        >
          <ArrowRight className="h-5 w-5" strokeWidth={2} />
        </button>
      </motion.div>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.6 }}
        className="mt-4 flex items-center justify-center gap-2 text-center text-sm text-ink-500"
      >
        AlphaSource discovers candidates dynamically from connected talent sources.
        <kbd className="rounded border border-white/[0.1] px-1.5 py-0.5 text-[10px] text-ink-500">⌘K</kbd>
      </motion.p>
    </form>
  );
});

export default SearchBar;
