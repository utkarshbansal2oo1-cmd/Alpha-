/**
 * Powers the "cursor-follow glow" micro-interaction on cards (Feature
 * Showcase, glass cards). Writes CSS custom properties instead of animating
 * React state, so the glow follows the mouse at native pointermove speed
 * with no re-render cost -- the .cursor-glow CSS class (styles/index.css)
 * reads --mx/--my for its radial-gradient position.
 */
export function useCursorGlow() {
  function onMouseMove(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - rect.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - rect.top}px`);
  }
  return { onMouseMove };
}
