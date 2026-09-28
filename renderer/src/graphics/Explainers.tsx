import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { EASE, FONT, Palette, RADIUS, SHADOW, SPRING } from "../theme";

// Explainer B-roll: full-frame motion graphics for lectures. Every beat time (`at`) is
// an edit second (absolute, like t0), so each element lands on the word that names it.

type Box = { w: number; h: number; palette: Palette; t0: number; vertical: boolean };

const useF = (t0: number) => {
  const { fps } = useVideoConfig();
  return (s: number) => Math.round((s - t0) * fps);
};

const Title: React.FC<{ text?: string; palette: Palette; vertical: boolean; k: number }> = ({ text, palette, vertical, k }) =>
  text ? (
    <div style={{ position: "absolute", left: vertical ? 72 : 120, top: vertical ? 90 : 90, fontFamily: FONT.sans, fontWeight: 600,
      fontSize: vertical ? 34 : 34, letterSpacing: "0.04em", textTransform: "uppercase", color: palette.muted, opacity: k }}>{text}</div>
  ) : null;

// ------------------------------------------------------------------ BigNumber
export const BigNumber: React.FC<Box & { value: number; decimals?: number; prefix?: string; suffix?: string; label: string; at: number; title?: string; sub?: string; subAt?: number }> = ({
  w, h, palette, t0, vertical, value, decimals = 0, prefix = "", suffix = "", label, at, title, sub, subAt,
}) => {
  const f = useCurrentFrame();
  const F = useF(t0);
  const k = interpolate(f, [F(at) - 24, F(at)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  const lk = interpolate(f, [F(at), F(at) + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  const sk = sub ? interpolate(f, [F(subAt ?? at + 1.2), F(subAt ?? at + 1.2) + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter }) : 0;
  const size = vertical ? 220 : 260;
  return (
    <div style={{ position: "absolute", inset: 0, width: w, height: h, display: "flex", flexDirection: "column", justifyContent: "center",
      paddingLeft: vertical ? 72 : 160 }}>
      <Title text={title} palette={palette} vertical={vertical} k={Math.min(1, f / 10)} />
      <div style={{ display: "flex", alignItems: "baseline", gap: 18, fontFamily: FONT.sans, fontWeight: 800, fontSize: size, letterSpacing: "-0.05em",
        fontVariantNumeric: "tabular-nums", color: palette.text, lineHeight: 0.95, opacity: Math.min(1, k * 3) }}>
        <span>{prefix}{(value * k).toFixed(decimals)}</span>
        {suffix ? <span style={{ fontSize: size * 0.4, fontWeight: 700, color: palette.accent, letterSpacing: "-0.02em" }}>{suffix}</span> : null}
      </div>
      <div style={{ width: 160 * lk, height: 4, background: palette.accent, marginTop: 26, borderRadius: 2 }} />
      <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: vertical ? 40 : 44, color: palette.text, marginTop: 26, opacity: lk,
        transform: `translateY(${(1 - lk) * 10}px)`, maxWidth: vertical ? 900 : 1300 }}>{label}</div>
      {sub ? <div style={{ fontFamily: FONT.serif, fontStyle: "italic", fontSize: vertical ? 40 : 44, color: palette.muted, marginTop: 18, opacity: sk }}>{sub}</div> : null}
    </div>
  );
};

// ------------------------------------------------------------------ Timeline (a hype curve)
export type Milestone = { year: string; label: string; at: number; level: number; winter?: boolean };
export const Timeline: React.FC<Box & { title?: string; points: Milestone[] }> = ({ w, h, palette, t0, vertical, title, points }) => {
  const f = useCurrentFrame();
  const F = useF(t0);
  const padX = vertical ? 90 : 180;
  const top = h * 0.24;
  const bottom = h * 0.74;
  const xs = points.map((_, i) => padX + ((w - padX * 2) * i) / Math.max(points.length - 1, 1));
  const ys = points.map((p) => bottom - (bottom - top) * p.level);
  // Draw the curve up to the latest reached point, easing between points.
  let reach = 0;
  points.forEach((p, i) => {
    const k = interpolate(f, [F(p.at) - 14, F(p.at)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
    if (k > 0) reach = i - 1 + k;
  });
  const path: string[] = [];
  for (let i = 0; i < points.length; i++) {
    if (i === 0) {
      path.push(`M ${xs[0]} ${ys[0]}`);
      continue;
    }
    const seg = Math.max(0, Math.min(1, reach - (i - 1)));
    if (seg <= 0) break;
    const mx = (xs[i - 1] + xs[i]) / 2;
    const ex = xs[i - 1] + (xs[i] - xs[i - 1]) * seg;
    const ey = ys[i - 1] + (ys[i] - ys[i - 1]) * seg;
    path.push(`C ${Math.min(mx, ex)} ${ys[i - 1]}, ${Math.min(mx, ex)} ${ey}, ${ex} ${ey}`);
  }
  return (
    <div style={{ position: "absolute", inset: 0, width: w, height: h }}>
      <Title text={title} palette={palette} vertical={vertical} k={Math.min(1, f / 10)} />
      <svg width={w} height={h} style={{ position: "absolute", inset: 0 }}>
        <line x1={padX} x2={w - padX} y1={bottom + 40} y2={bottom + 40} stroke={palette.text} strokeOpacity={0.25} strokeWidth={2} />
        <path d={path.join(" ")} fill="none" stroke={palette.accent} strokeWidth={5} strokeLinecap="round" />
      </svg>
      {points.map((p, i) => {
        const k = spring({ frame: f - F(p.at), fps: 30, config: SPRING.settle });
        if (f < F(p.at) - 2) return null;
        const above = i % 2 === 0;
        return (
          <div key={i} style={{ position: "absolute", left: xs[i], top: ys[i], transform: "translate(-50%, -50%)" }}>
            <div style={{ width: 22, height: 22, borderRadius: 11, background: p.winter ? palette.cool : palette.accent, transform: `scale(${k})`,
              boxShadow: `0 0 0 6px rgba(0,0,0,.35)` }} />
            <div style={{ position: "absolute", left: "50%", top: above ? -150 : 40, transform: `translate(-50%, ${(1 - k) * 10}px)`, opacity: k,
              width: 300, textAlign: "center" }}>
              <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: 46, letterSpacing: "-0.03em", fontVariantNumeric: "tabular-nums",
                color: p.winter ? palette.cool : palette.text }}>{p.year}</div>
              <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: 28, color: palette.muted, marginTop: 4, lineHeight: 1.15 }}>{p.label}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ------------------------------------------------------------------ Tokens
export const Tokens: React.FC<Box & { title?: string; word: string; pieces: string[]; ids: number[]; at: number; idsAt?: number; note?: string }> = ({
  w, h, palette, t0, vertical, title, word, pieces, ids, at, idsAt, note,
}) => {
  const f = useCurrentFrame();
  const F = useF(t0);
  const split = interpolate(f, [F(at), F(at) + 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
  const idk = interpolate(f, [F(idsAt ?? at + 1.5), F(idsAt ?? at + 1.5) + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  const size = vertical ? 110 : 150;
  const colors = [palette.accent, palette.cool, "#C9A36A", "#9FD8A8", "#E6A0C4"];
  return (
    <div style={{ position: "absolute", inset: 0, width: w, height: h, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      <Title text={title} palette={palette} vertical={vertical} k={Math.min(1, f / 10)} />
      <div style={{ fontFamily: FONT.sans, fontSize: 34, color: palette.muted, marginBottom: 40, opacity: 1 - split }}>“{word}”</div>
      <div style={{ display: "flex", gap: 28 * split + 4 }}>
        {pieces.map((p, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
            <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: size, letterSpacing: "-0.03em", color: palette.text,
              padding: `${6 + 10 * split}px ${4 + 22 * split}px`, borderRadius: RADIUS,
              background: `rgba(255,255,255,${0.06 * split})`, boxShadow: `inset 0 -${8 * split}px 0 ${colors[i % colors.length]}` }}>{p}</div>
            <div style={{ fontFamily: FONT.mono, fontWeight: 500, fontSize: 48, color: colors[i % colors.length], opacity: idk,
              transform: `translateY(${(1 - idk) * -14}px)`, fontVariantNumeric: "tabular-nums" }}>{ids[i]}</div>
          </div>
        ))}
      </div>
      {note ? <div style={{ fontFamily: FONT.serif, fontStyle: "italic", fontSize: 44, color: palette.muted, marginTop: 70, opacity: idk }}>{note}</div> : null}
    </div>
  );
};

// ------------------------------------------------------------------ NextToken (probability bars + temperature)
export const NextToken: React.FC<Box & { title?: string; prompt: string; options: { word: string; p: number }[]; at: number; pickAt?: number; temps?: { t: number; at: number }[] }> = ({
  w, h, palette, t0, vertical, title, prompt, options, at, pickAt, temps = [],
}) => {
  const f = useCurrentFrame();
  const F = useF(t0);
  // Temperature reshapes the distribution: p^(1/T), renormalised.
  let T = 1;
  temps.forEach((tp, i) => {
    const prev = i === 0 ? 1 : temps[i - 1].t;
    const k = interpolate(f, [F(tp.at), F(tp.at) + 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
    if (f >= F(tp.at)) T = prev + (tp.t - prev) * k;
  });
  const raw = options.map((o) => Math.pow(o.p, 1 / Math.max(T, 0.05)));
  const sum = raw.reduce((a, b) => a + b, 0);
  const probs = raw.map((r) => r / sum);
  const barMax = vertical ? 620 : 900;
  const pick = pickAt !== undefined ? interpolate(f, [F(pickAt), F(pickAt) + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter }) : 0;
  return (
    <div style={{ position: "absolute", inset: 0, width: w, height: h, paddingLeft: vertical ? 72 : 180, paddingTop: vertical ? 300 : 230 }}>
      <Title text={title} palette={palette} vertical={vertical} k={Math.min(1, f / 10)} />
      <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: vertical ? 64 : 78, letterSpacing: "-0.03em", color: palette.text }}>
        {prompt}{" "}
        <span style={{ color: pick > 0 ? palette.accent : palette.muted, borderBottom: `4px solid ${palette.muted}`, display: "inline-block", minWidth: 180 }}>
          {pick > 0 ? options[0].word : " "}
        </span>
      </div>
      <div style={{ marginTop: 60, display: "flex", flexDirection: "column", gap: 20 }}>
        {options.map((o, i) => {
          const k = interpolate(f, [F(at) + i * 3, F(at) + i * 3 + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
          return (
            <div key={o.word} style={{ display: "flex", alignItems: "center", gap: 26, opacity: k }}>
              <div style={{ width: 170, fontFamily: FONT.sans, fontWeight: 600, fontSize: 40, color: palette.text, textAlign: "right" }}>{o.word}</div>
              <div style={{ height: 34, width: barMax * probs[i] * k, background: i === 0 ? palette.accent : "rgba(244,241,234,.35)", borderRadius: 6 }} />
              <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: 32, color: palette.muted, fontVariantNumeric: "tabular-nums" }}>
                {(probs[i] * 100).toFixed(0)}%
              </div>
            </div>
          );
        })}
      </div>
      {temps.length ? (
        <div style={{ marginTop: 50, fontFamily: FONT.sans, fontWeight: 600, fontSize: 36, color: palette.cool, fontVariantNumeric: "tabular-nums" }}>
          temperature {T.toFixed(1)}
        </div>
      ) : null}
    </div>
  );
};

// ------------------------------------------------------------------ Steps (a pipeline)
export const Steps: React.FC<Box & { title?: string; steps: { label: string; sub?: string; at: number }[] }> = ({ w, h, palette, t0, vertical, title, steps }) => {
  const f = useCurrentFrame();
  const F = useF(t0);
  const n = steps.length;
  const gap = 36;
  const cw = vertical ? w - 144 : (w - 360 - gap * (n - 1)) / n;
  const labelSize = vertical ? 52 : Math.min(50, cw / 6.2);
  const subSize = vertical ? 30 : Math.min(30, cw / 9.5);
  return (
    <div style={{ position: "absolute", inset: 0, width: w, height: h, display: "flex", flexDirection: vertical ? "column" : "row", gap,
      alignItems: "center", justifyContent: "center", padding: vertical ? "0 72px" : "0 180px" }}>
      <Title text={title} palette={palette} vertical={vertical} k={Math.min(1, f / 10)} />
      {steps.map((s, i) => {
        const k = interpolate(f, [F(s.at) - 6, F(s.at) + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
        const active = f >= F(s.at) && (i === n - 1 || f < F(steps[i + 1].at));
        return (
          <div key={i} style={{ width: cw, minHeight: vertical ? 220 : 340, borderRadius: RADIUS, padding: "36px 34px",
            background: active ? palette.paper : "rgba(244,241,234,.06)", color: active ? palette.ink : palette.text,
            border: `1px solid rgba(244,241,234,${active ? 0 : 0.15})`, boxShadow: active ? SHADOW.card : "none",
            opacity: 0.25 + 0.75 * k, transform: `translateY(${(1 - k) * 20}px)` }}>
            <div style={{ fontFamily: FONT.sans, fontWeight: 600, fontSize: 30, color: active ? palette.accentInk : palette.accent, fontVariantNumeric: "tabular-nums" }}>
              {String(i + 1).padStart(2, "0")}
            </div>
            <div style={{ fontFamily: FONT.sans, fontWeight: 800, fontSize: labelSize, letterSpacing: "-0.03em", marginTop: 16, lineHeight: 1.02 }}>{s.label}</div>
            {s.sub ? <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: subSize, marginTop: 16, opacity: 0.75, lineHeight: 1.25 }}>{s.sub}</div> : null}
          </div>
        );
      })}
    </div>
  );
};
