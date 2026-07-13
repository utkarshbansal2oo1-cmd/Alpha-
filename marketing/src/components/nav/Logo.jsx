export default function Logo({ size = "default" }) {
  const titleClass = size === "small" ? "text-lg" : "text-xl";
  return (
    <div className="flex flex-col leading-none select-none">
      <span className={`${titleClass} font-bold tracking-tight text-text-primary`}>
        AlphaSource <span className="accent-text">AI</span>
      </span>
      <span className="text-[11px] tracking-[0.08em] uppercase text-text-tertiary mt-1">
        Powered by AlphaRecrewt
      </span>
    </div>
  );
}
