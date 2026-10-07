import React from "react";
import { AbsoluteFill, interpolate, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import { fitText } from "@remotion/layout-utils";
import { EASE, FONT, Format, Palette, isVertical } from "../theme";

// The spent moment: one huge word behind the speaker. Layers: (plate below) a 16% dim,
// the word, then the speaker cut out by Apple Vision (fg: alpha WebM of this span).
// Speaker layout only (the plate must be untransformed), steady framing, no cut inside.
export const TextBehind: React.FC<{
  format: Format; palette: Palette; dur: number; t0: number;
  text: string; fg: string; y?: number; size?: number; accent?: boolean; serif?: boolean; faceY?: number;
}> = ({ format, palette, dur, text, fg, y, size, accent, serif, faceY }) => {
  const f = useCurrentFrame();
  const v = isVertical(format);
  // Fit the word to the frame width (with margins), capped so short words do not explode.
  const fitted = fitText({ text, withinWidth: v ? 1000 : 1720, fontFamily: serif ? FONT.serif : FONT.sans,
    fontWeight: serif ? 400 : 800, letterSpacing: serif ? "-0.01em" : "-0.05em", validateFontIsLoaded: false }).fontSize;
  const s = size ?? Math.min(fitted, v ? 380 : 420);
  // Centre the word on the face so the head and shoulders pass in front of it.
  const top = y ?? (faceY !== undefined ? Math.max(v ? 120 : 48, faceY - s * 1.02) : v ? 330 : 120);
  const rise = interpolate(f, [0, 27], [0, 1], { extrapolateRight: "clamp", easing: EASE.power3 });
  const out = interpolate(f, [dur - 12, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.exit });
  const dim = interpolate(f, [0, 10], [0, 0.16], { extrapolateRight: "clamp" }) * out;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: `rgba(0,0,0,${dim})` }} />
      <AbsoluteFill style={{ alignItems: "center", overflow: "hidden" }}>
        <div style={{ position: "absolute", top, width: "100%", textAlign: "center", whiteSpace: "nowrap",
          transform: `translateY(${(1 - rise) * 0.48 * s}px)`, clipPath: `inset(0 0 ${(1 - rise) * 40}% 0)`,
          fontFamily: serif ? FONT.serif : FONT.sans, fontStyle: serif ? "italic" : "normal", fontWeight: serif ? 400 : 800,
          fontSize: s, lineHeight: 0.9, letterSpacing: serif ? "-0.01em" : "-0.05em",
          color: accent ? palette.accent : palette.text, opacity: 0.94 * out }}>
          {text}
        </div>
      </AbsoluteFill>
      {/* Positioned, so it paints above the absolutely positioned word (static elements paint below). */}
      <AbsoluteFill>
        <OffthreadVideo src={staticFile(fg)} transparent muted style={{ width: "100%", height: "100%" }} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
