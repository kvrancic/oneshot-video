import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "./theme";

const out = Easing.bezier(0.16, 1, 0.3, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// Lines rise out of a mask, one after another. Frames are relative to the enclosing Seg.
export const MaskLines: React.FC<{
  lines: React.ReactNode[];
  size: number;
  delay?: number;
  stagger?: number;
  font?: "display" | "serif";
  exitAt?: number; // frame where the lines leave upward
  align?: "left" | "center";
  lineHeight?: number;
  color?: string;
}> = ({ lines, size, delay = 0, stagger = 4, font = "display", exitAt, align = "left", lineHeight = 0.95, color = "#fff" }) => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const display = font === "display";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: align === "center" ? "center" : "flex-start" }}>
      {lines.map((l, i) => {
        const p = interpolate(frame, [delay + i * stagger, delay + i * stagger + 11], [0, 1], { ...clamp, easing: out });
        const q = exitAt === undefined ? 0 : interpolate(frame, [exitAt + i * 2, exitAt + i * 2 + 7], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
        return (
          <div key={i} style={{ overflow: "hidden", paddingBottom: size * 0.06, marginBottom: -size * 0.06 }}>
            <div style={{
              transform: `translateY(${(1 - p) * 105 - q * 105}%) skewY(${(1 - p) * 4}deg)`,
              fontFamily: display ? th.display : th.serif, fontWeight: display ? 900 : 400, fontStyle: display ? "normal" : "italic",
              fontStretch: display ? `${th.displayStretch}%` : undefined, fontSize: size, lineHeight, color,
              letterSpacing: display ? "-0.02em" : "-0.01em", textTransform: display ? "uppercase" : "none", whiteSpace: "nowrap",
              textShadow: "0 6px 40px rgba(0,0,0,.35)",
            }}>{l}</div>
          </div>
        );
      })}
    </div>
  );
};

// A word slams in: overshoot scale, blur to sharp. at is a frame relative to the Seg. A long word
// near the frame's width needs a smaller overshoot (1.15) or its first frames run off the edges.
export const Slam: React.FC<{ text: string; size: number; at?: number; color?: string; font?: "display" | "serif"; overshoot?: number }> = ({ text, size, at = 0, color = "#fff", font = "display", overshoot = 1.5 }) => {
  const frame = useCurrentFrame() - at;
  const th = useTheme();
  if (frame < 0) return null;
  const display = font === "display";
  return (
    <div style={{
      transform: `scale(${interpolate(frame, [0, 5, 10], [overshoot, 0.97, 1], clamp)})`, filter: `blur(${interpolate(frame, [0, 5], [14, 0], clamp)}px)`,
      opacity: interpolate(frame, [0, 2], [0.85, 1], clamp), fontFamily: display ? th.display : th.serif, fontWeight: display ? 900 : 400,
      fontStyle: display ? "normal" : "italic", fontStretch: `${th.displayStretch}%`, fontSize: size, lineHeight: 0.9, color,
      textTransform: display ? "uppercase" : "none", letterSpacing: "-0.02em", whiteSpace: "nowrap", textShadow: "0 8px 50px rgba(0,0,0,.4)",
    }}>{text}</div>
  );
};

// A mono label with an accent chip, typed on. At least 40 px for anything shown on a big screen.
export const Label: React.FC<{ text: string; chip?: string; at?: number; size?: number }> = ({ text, chip, at = 0, size = 26 }) => {
  const frame = useCurrentFrame() - at;
  const th = useTheme();
  if (frame < 0) return null;
  const n = Math.floor(interpolate(frame, [0, Math.max(1, text.length * 0.6)], [0, text.length], clamp));
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: th.mono, fontWeight: 600, fontSize: size, letterSpacing: "0.2em", color: "rgba(255,255,255,.9)" }}>
      {chip && <span style={{ background: th.accent, color: "#fff", padding: `${size * 0.25}px ${size * 0.45}px`, letterSpacing: "0.12em" }}>{chip}</span>}
      <span>{text.slice(0, n)}{n < text.length ? "▍" : ""}</span>
    </div>
  );
};

// A dark gradient behind text so it reads on any footage.
export const Scrim: React.FC<{ side?: "left" | "bottom" | "center"; strength?: number }> = ({ side = "left", strength = 0.7 }) => {
  const bg = side === "left"
    ? `linear-gradient(90deg, rgba(0,0,0,${strength}) 0%, rgba(0,0,0,${strength * 0.5}) 45%, rgba(0,0,0,0) 75%)`
    : side === "bottom"
      ? `linear-gradient(0deg, rgba(0,0,0,${strength}) 0%, rgba(0,0,0,0) 60%)`
      : `radial-gradient(ellipse at center, rgba(0,0,0,${strength}) 0%, rgba(0,0,0,${strength * 0.3}) 60%, rgba(0,0,0,0) 100%)`;
  return <AbsoluteFill style={{ background: bg }} />;
};

// A checkerboard wipe: squares grow along a diagonal to cover the frame, then shrink away.
// cover: [start, full] frames; uncover: [start, gone]. A brand transition: use it twice, not every cut.
export const Checker: React.FC<{ cover: [number, number]; uncover: [number, number]; cell?: number; reverse?: boolean; colors?: [string, string] }> = ({ cover, uncover, cell = 160, reverse, colors }) => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const { width, height } = useVideoConfig();
  const [c0, c1] = colors ?? [th.accent, th.accent2];
  const cols = Math.ceil(width / cell), rows = Math.ceil(height / cell), maxD = cols + rows;
  const squares: React.ReactNode[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const k = ((reverse ? cols - 1 - c : c) + r) / maxD;
      const a = interpolate(frame, [cover[0] + k * (cover[1] - cover[0]) * 0.6, cover[0] + (0.4 + k * 0.6) * (cover[1] - cover[0])], [0, 1], { ...clamp, easing: out });
      const b = interpolate(frame, [uncover[0] + k * (uncover[1] - uncover[0]) * 0.6, uncover[0] + (0.4 + k * 0.6) * (uncover[1] - uncover[0])], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
      const s = a * (1 - b);
      if (s <= 0.001) continue;
      squares.push(<div key={`${r}-${c}`} style={{ position: "absolute", left: c * cell, top: r * cell, width: cell, height: cell, background: (r + c) % 2 === 0 ? c0 : c1, transform: `scale(${s * 1.02})` }} />);
    }
  }
  return <AbsoluteFill style={{ pointerEvents: "none" }}>{squares}</AbsoluteFill>;
};
