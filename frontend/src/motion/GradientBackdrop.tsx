/**
 * DECORATIVE: slow-moving colour glows behind the whole site. Colours come from the current mode's CSS variables,
 * so they cross-fade when the mode changes. It shows no data and carries no text. Motion stops under reduced motion.
 */
export default function GradientBackdrop() {
  return (
    <div aria-hidden="true" className="backdrop-layer pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="backdrop-glow backdrop-glow-a" />
      <div className="backdrop-glow backdrop-glow-b" />
      <div className="backdrop-glow backdrop-glow-c" />
    </div>
  );
}
