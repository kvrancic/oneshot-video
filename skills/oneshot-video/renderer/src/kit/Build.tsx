import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme } from "./theme";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// The build to a peak. Wraps a plate and escalates into the hit: an accelerating push, a kick on
// every beat, a tremor that grows through the last bar, a closing vignette and (optionally) a charge
// bar that fills one step per beat. Times are seconds from the start of the enclosing Seg.
// An opener ends on the peak (build, impact, a few seconds of payoff), never on a calming fade.
export const BuildTo: React.FC<{ hit: number; beats?: number[]; chargeFrom?: number; push?: [number, number]; children: React.ReactNode }> = ({ hit, beats = [], chargeFrom, push = [1.06, 1.3], children }) => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const s = interpolate(t, [0, hit], push, { ...clamp, easing: Easing.in(Easing.cubic) });
  const last = Math.max(-1, ...beats.filter((b) => b <= t + 0.001));
  const kick = last < 0 ? 0 : interpolate(t - last, [0, 0.22], [0.028, 0], clamp);
  const build = interpolate(t, [hit - 1.7, hit], [0, 1], clamp);
  const sx = Math.sin(frame * 2.9) * 16 * build * build, sy = Math.cos(frame * 2.3) * 11 * build * build;
  const vig = interpolate(t, [0, hit], [0, 1], clamp);
  const steps = chargeFrom === undefined ? [] : beats.filter((b) => b > chargeFrom - 0.05 && b < hit - 0.05);
  const charge = chargeFrom === undefined || t < chargeFrom ? 0 : Math.min(1, (steps.filter((b) => b <= t).length + 1) / (steps.length + 1));
  const glow = chargeFrom === undefined ? 0 : interpolate(t, [chargeFrom, hit], [0.3, 1], clamp);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `translate(${sx}px, ${sy}px) scale(${s + kick})` }}>{children}</AbsoluteFill>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at center, rgba(0,0,0,0) ${60 - 22 * vig}%, rgba(0,0,0,${0.3 + 0.4 * vig}) 100%)` }} />
      {chargeFrom !== undefined && (
        <div style={{ position: "absolute", left: "6%", right: "6%", bottom: "4%", height: 24, background: "rgba(255,255,255,.18)" }}>
          <div style={{ width: `${charge * 100}%`, height: "100%", background: th.accent, boxShadow: `0 0 ${20 + 50 * glow}px ${th.accent}, 0 0 ${10 * glow}px #fff` }} />
        </div>
      )}
    </AbsoluteFill>
  );
};

// One shouted or sung word at a time, low in the frame (over torsos, never faces), each one
// bigger than the last; hot grows a glow up to the hit. at / until: seconds from the Seg start.
export const ShoutWord: React.FC<{ text: string; at: number; until: number; size: number; hot?: boolean; bottom?: number }> = ({ text, at, until, size, hot, bottom = 96 }) => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const { fps } = useVideoConfig();
  const a = Math.round(at * fps), b = Math.round(until * fps);
  if (frame < a || frame >= b) return null;
  const k = frame - a;
  const grow = hot ? interpolate(frame, [a, b], [0, 1], clamp) : 0;
  const s = interpolate(k, [0, 4, 8], [1.6, 0.95, 1], clamp) * (1 + 0.16 * grow);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-end", paddingBottom: bottom }}>
      <div style={{ transform: `scale(${s})`, transformOrigin: "50% 100%", filter: `blur(${interpolate(k, [0, 4], [12, 0], clamp)}px)`,
        fontFamily: th.display, fontWeight: 900, fontStretch: `${th.displayStretch}%`, fontSize: size, lineHeight: 1, color: "#fff",
        textTransform: "uppercase", whiteSpace: "nowrap", textShadow: `0 8px 40px rgba(0,0,0,.7), 0 0 ${90 * grow}px ${th.accent}` }}>{text}</div>
    </AbsoluteFill>
  );
};

// Squares flying out from behind the hero word on the impact frame (put it under the word, so the
// word is readable on the frame after the hit; a covering wipe would hide it).
export const Burst: React.FC<{ count?: number; colors?: [string, string]; frames?: number; origin?: [number, number] }> = ({ count = 46, colors, frames = 18, origin }) => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const { width, height } = useVideoConfig();
  if (frame > frames) return null;
  const [ox, oy] = origin ?? [width / 2, height / 2];
  const [c0, c1] = colors ?? [th.accent, th.accent2];
  const p = interpolate(frame, [1, frames - 2], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const o = interpolate(frame, [1, 3, frames - 6, frames], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: count }, (_, i) => {
        const ang = (i / count) * Math.PI * 2 + (i % 3) * 0.37;
        const r = 60 + p * width * 0.65 * (0.75 + ((i * 37) % 10) / 10);
        const size = 70 + ((i * 13) % 5) * 22;
        return <div key={i} style={{ position: "absolute", left: ox + Math.cos(ang) * r - size / 2, top: oy + Math.sin(ang) * r * 0.62 - size / 2,
          width: size, height: size, background: i % 2 ? c1 : c0, opacity: o, transform: `rotate(${p * (i % 2 ? 140 : -140)}deg)` }} />;
      })}
    </AbsoluteFill>
  );
};
