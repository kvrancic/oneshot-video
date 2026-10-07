import React from "react";
import { useTheme } from "./theme";

// A split-flap departure board that spells a word letter by letter, each letter locking on a story
// beat. Hold the hero letter (usually the first) for the musical hit: it must be settled on that frame.

// Letters that look like the given ones (a spinner that shows "COSTON" before "BOSTON" reads as a typo).
const LOOKALIKE: Record<string, string> = {
  B: "PRDE8", C: "GOQ", D: "OB0", E: "FB", F: "EP", G: "CO6", I: "1LJ", J: "I", K: "X", L: "I", M: "NW", N: "MH", O: "QDC0", P: "RBF",
  Q: "O", R: "PB", S: "5Z", T: "I7", U: "V", V: "UY", W: "M", X: "K", Y: "V", Z: "S2",
};

// Spinner alphabet for a word: letters only (digits read as a glitch), never the word's own letters
// (a spinner that briefly spells the answer gives it away) and never a lookalike of the hero letter.
export const alphabetFor = (word: string, hero = 0) => {
  const banned = new Set((word.toUpperCase() + (LOOKALIKE[word[hero]?.toUpperCase()] ?? "")).split(""));
  return "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").filter((c) => !banned.has(c)).join("");
};

const hash = (a: number, b: number) => {
  let h = (a * 374761393 + b * 668265263) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return Math.abs(h ^ (h >>> 16));
};

// A spin interval [a, b) in frames; decel spins slow down like a slot machine.
export type Spin = { a: number; b: number; decel?: boolean };
export type CellPlan = { lock: number; spins: Spin[] };

// Plans for every cell: one opening spin (staggered per cell, decelerating), short flutters at
// each frame in `flutters` until the cell locks, and the lock frames. A lock is when the letter
// is settled: the flip starts 3 frames earlier, so pass the hit frame itself.
export const planFromLocks = (word: string, locks: number[], open: [number, number], flutters: number[] = []): CellPlan[] =>
  word.split("").map((_, i) => {
    const lock = locks[i];
    const spins: Spin[] = [{ a: open[0], b: Math.min(open[1] + i * 2, lock - 3), decel: true }];
    for (const c of flutters) if (c + 13 + i < lock - 3) spins.push({ a: c + 2, b: c + 13 + i });
    return { lock: lock - 3, spins };
  });

const stepAt = (sp: Spin, fr: number) => {
  if (!sp.decel) return Math.floor((fr - sp.a) / 2);
  // ease-out that never stalls: the last letter dwells 3 to 5 frames
  const u = (fr - sp.a) / (sp.b - sp.a), k = 0.6, total = (sp.b - sp.a) / 3.2;
  return Math.floor((total * (1 - (1 - k * u) ** 2)) / (1 - (1 - k) ** 2));
};

const state = (i: number, fr: number, target: string, plan: CellPlan, alph: string): { ch: string; at: number } => {
  if (fr >= plan.lock) return { ch: target, at: plan.lock };
  for (const sp of plan.spins) {
    if (fr >= sp.a && fr < sp.b) {
      const n = stepAt(sp, fr);
      let at = fr;
      while (at > sp.a && stepAt(sp, at - 1) === n) at--;
      return { ch: alph[hash(i + 1, n + sp.a) % alph.length], at };
    }
  }
  const ended = plan.spins.filter((sp) => sp.b <= fr).map((sp) => sp.b);
  return { ch: " ", at: ended.length ? Math.max(...ended) : -99 };
};

const Half: React.FC<{ ch: string; w: number; h: number; top: boolean; color: string; font: string; style?: React.CSSProperties }> = ({ ch, w, h, top, color, font, style }) => (
  <div style={{ position: "absolute", left: 0, width: w, height: h / 2, top: top ? 0 : h / 2, overflow: "hidden",
    background: top ? "linear-gradient(#26262d,#1b1b21)" : "linear-gradient(#18181d,#121216)", borderRadius: top ? `${h * 0.07}px ${h * 0.07}px 0 0` : `0 0 ${h * 0.07}px ${h * 0.07}px`, ...style }}>
    <div style={{ position: "absolute", left: 0, width: w, height: h, top: top ? 0 : -h / 2, display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: font, fontWeight: 700, fontSize: h * 0.74, color, lineHeight: 1 }}>{ch}</div>
  </div>
);

const Cell: React.FC<{ i: number; frame: number; target: string; plan: CellPlan; w: number; alph: string; fire?: number }> = ({ i, frame, target, plan, w, alph, fire }) => {
  const th = useTheme();
  const h = w * 1.38;
  const cur = state(i, frame, target, plan, alph);
  const prev = state(i, cur.at - 1, target, plan, alph);
  const t = Math.min(1, Math.max(0, (frame - cur.at) / 3)); // a flip lasts 3 frames
  const color = frame >= plan.lock ? "#fff" : "#F2EEE8";
  const glow = frame >= plan.lock ? Math.max(0, 1 - (frame - plan.lock) / 18) : 0;
  const g = fire === undefined || frame < plan.lock ? 0 : Math.max(0, 1 - Math.abs(frame - fire) / 6);
  return (
    <div style={{ position: "relative", width: w, height: h, perspective: h * 4, borderRadius: h * 0.07,
      boxShadow: `0 ${h * 0.05}px ${h * 0.12}px rgba(0,0,0,.55)${glow > 0 ? `, 0 0 ${h * 0.5 * glow}px ${th.accent}` : ""}` }}>
      <Half ch={cur.ch} w={w} h={h} top color={color} font={th.mono} />
      <Half ch={t < 1 ? prev.ch : cur.ch} w={w} h={h} top={false} color={color} font={th.mono} />
      {t < 0.5 && <Half ch={prev.ch} w={w} h={h} top color={color} font={th.mono} style={{ transformOrigin: "50% 100%", transform: `rotateX(${-180 * t}deg)`, filter: `brightness(${1 - t})` }} />}
      {t >= 0.5 && t < 1 && <Half ch={cur.ch} w={w} h={h} top={false} color={color} font={th.mono} style={{ transformOrigin: "50% 0%", transform: `rotateX(${180 * (1 - t)}deg)`, filter: `brightness(${t})` }} />}
      <div style={{ position: "absolute", left: 0, right: 0, top: h / 2 - 1, height: 2, background: "rgba(0,0,0,.85)" }} />
      {frame >= plan.lock && <div style={{ position: "absolute", left: w * 0.12, right: w * 0.12, bottom: h * 0.06, height: Math.max(2, h * (0.025 + 0.03 * g)),
        background: g > 0.5 ? "#fff" : th.accent, borderRadius: 2, boxShadow: g > 0 ? `0 0 ${h * 0.3 * g}px ${th.accent}` : undefined }} />}
    </div>
  );
};

// frame is the film frame (the board usually lives across several scenes, so it takes absolute time).
// Reserve its full size from the first frame: a subline that appears later must not shift the word.
export const Board: React.FC<{ frame: number; word: string; plans: CellPlan[]; w: number; label?: string; sub?: string; fireAt?: number; alphabet?: string }> = ({ frame, word, plans, w, label = "NEXT STOP", sub, fireAt, alphabet }) => {
  const th = useTheme();
  const alph = alphabet ?? alphabetFor(word);
  return (
    <div style={{ display: "inline-flex", flexDirection: "column", gap: w * 0.22, padding: `${w * 0.32}px ${w * 0.36}px`,
      background: "rgba(8,8,11,.82)", border: "1px solid rgba(255,255,255,.12)", borderRadius: w * 0.16, backdropFilter: "blur(14px)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontFamily: th.mono, fontWeight: 600, fontSize: w * 0.2, letterSpacing: "0.22em", color: "rgba(255,255,255,.75)" }}>
        <span style={{ display: "flex", alignItems: "center", gap: w * 0.12 }}>
          <span style={{ width: w * 0.12, height: w * 0.12, background: th.accent, display: "inline-block", opacity: frame % 30 < 18 ? 1 : 0.25 }} />
          {label}
        </span>
        <span style={{ color: "rgba(255,255,255,.45)", visibility: sub ? "visible" : "hidden" }}>{sub ?? "—"}</span>
      </div>
      <div style={{ display: "flex", gap: w * 0.12 }}>
        {word.toUpperCase().split("").map((c, i) => (
          <Cell key={i} i={i} frame={frame} target={c} plan={plans[i]} w={w} alph={alph} fire={fireAt === undefined ? undefined : fireAt + i * 2} />
        ))}
      </div>
    </div>
  );
};
