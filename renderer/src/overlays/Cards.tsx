import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { EASE, FONT, Format, HAIRLINE, Palette, RADIUS, SAFE, SHADOW, SPRING, isVertical } from "../theme";
import { envelope, maskUp } from "./util";

type Base = { format: Format; palette: Palette; dur: number };

// ----------------------------------------------------------------- HookBar
// The hook headline: a paper card top-left for the first seconds, then it collapses
// to a small persistent label (or leaves). Cold-reader words, one number max.
export const HookBar: React.FC<Base & { text: string; collapseAt?: number; persist?: boolean; treatment?: "paper" | "float"; instant?: boolean }> = ({
  format, palette, dur, text, collapseAt, persist, treatment = "paper", instant,
}) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const v = isVertical(format);
  const safe = SAFE[format];
  const size = v ? 60 : 52;
  // A hook that opens the clip is fully drawn on frame 0: the first frame is the thumbnail.
  const env = envelope(f, dur, 10, 8);
  const k = instant ? 1 : env.k;
  const o = env.o;
  const cAt = collapseAt !== undefined ? Math.round(collapseAt * fps) : undefined;
  const c = cAt !== undefined && persist ? interpolate(f, [cAt, cAt + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move }) : 0;
  const scale = 1 - 0.38 * c;
  const lines = text.split("\n");
  const paper = treatment === "paper";
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: safe.x0,
          top: v ? 170 : 72,
          maxWidth: (safe.x1 - safe.x0) * (v ? 1 : 0.6),
          transform: `scale(${scale}) scaleY(${0.9 + 0.1 * k})`,
          transformOrigin: "0 0",
          opacity: o * (1 - 0.15 * c) * Math.min(1, k * 1.4),
          background: paper ? palette.paper : "transparent",
          color: paper ? palette.ink : palette.text,
          borderRadius: RADIUS,
          padding: paper ? "20px 28px 22px" : 0,
          boxShadow: paper ? SHADOW.card : "none",
          textShadow: paper ? "none" : SHADOW.display,
        }}
      >
        {lines.map((ln, i) => {
          const kk = instant ? 1 : interpolate(f, [3 * i + 2, 3 * i + 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
          return (
            <div
              key={i}
              style={{
                fontFamily: FONT.sans,
                fontWeight: 700,
                fontSize: size,
                lineHeight: 1.06,
                letterSpacing: "-0.022em",
                clipPath: maskUp(kk),
                transform: `translateY(${(1 - kk) * 14}px)`,
                textWrap: "balance",
              }}
            >
              {ln}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------------- NameTag
export const NameTag: React.FC<Base & { name: string; role?: string; x?: number; y?: number }> = ({ format, palette, dur, name, role, x, y }) => {
  const f = useCurrentFrame();
  const v = isVertical(format);
  const safe = SAFE[format];
  const { o } = envelope(f, dur, 12, 7);
  const line = interpolate(f, [0, 9], [0, 1], { extrapolateRight: "clamp", easing: EASE.enter });
  const n = interpolate(f, [3, 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  const r = interpolate(f, [7, 17], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  const top = y ?? (v ? 1040 : 780);
  return (
    <AbsoluteFill style={{ opacity: o, transform: `translateY(${(1 - o) * -6}px)` }}>
      <div style={{ position: "absolute", left: x ?? safe.x0, top, display: "flex", gap: 18 }}>
        <div style={{ width: HAIRLINE, background: palette.accent, transform: `scaleY(${line})`, transformOrigin: "top" }} />
        <div>
          <div style={{ fontFamily: FONT.sans, fontWeight: 600, fontSize: v ? 40 : 36, letterSpacing: "-0.01em", color: palette.text,
            textShadow: SHADOW.body, clipPath: maskUp(n), transform: `translateY(${(1 - n) * 12}px)` }}>{name}</div>
          {role ? (
            <div style={{ fontFamily: FONT.sans, fontWeight: 400, fontSize: v ? 30 : 26, color: palette.text, opacity: 0.78,
              textShadow: SHADOW.body, clipPath: maskUp(r), transform: `translateY(${(1 - r) * 12}px)`, marginTop: 4 }}>{role}</div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------------- KeywordChip
export const KeywordChip: React.FC<Base & { text: string; x?: number; y?: number; dot?: boolean }> = ({ format, palette, dur, text, x, y, dot = true }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const v = isVertical(format);
  const s = spring({ frame: f, fps, config: SPRING.snap });
  const { o } = envelope(f, dur, 1, 6);
  return (
    <div style={{ position: "absolute", left: x ?? SAFE[format].x0, top: y ?? (v ? 520 : 240), opacity: o * Math.min(1, s * 1.5),
      transform: `translateY(${(1 - s) * 8}px) scale(${0.96 + 0.04 * s})`, transformOrigin: "0 50%",
      display: "flex", alignItems: "center", gap: 12, padding: "12px 20px", borderRadius: RADIUS,
      background: "rgba(17,17,17,.72)", border: "1px solid rgba(244,241,234,.18)",
      fontFamily: FONT.sans, fontWeight: 600, fontSize: v ? 40 : 34, color: palette.text, letterSpacing: "-0.01em" }}>
      {dot ? <div style={{ width: 10, height: 10, borderRadius: 5, background: palette.accent }} /> : null}
      {text}
    </div>
  );
};

// ----------------------------------------------------------------- QuoteCard
export const QuoteCard: React.FC<Base & { lines: string[]; who?: string; y?: number }> = ({ format, palette, dur, lines, who, y }) => {
  const f = useCurrentFrame();
  const v = isVertical(format);
  const { k, o } = envelope(f, dur, 15, 9);
  const w = v ? 936 : 1100;
  const size = v ? 64 : 56;
  return (
    <AbsoluteFill style={{ alignItems: "center", opacity: o }}>
      <div style={{ position: "absolute", top: y ?? (v ? 420 : 250), width: w, padding: v ? "56px 64px" : "48px 64px", background: palette.paper,
        borderRadius: RADIUS, boxShadow: SHADOW.card, transform: `translateY(${(1 - k) * 40}px)`, opacity: k }}>
        <div style={{ position: "relative" }}>
          <span style={{ position: "absolute", left: -size * 0.42, top: -size * 0.08, fontFamily: FONT.serif, fontSize: size * 1.4,
            color: palette.accentInk, lineHeight: 1 }}>“</span>
          {lines.map((ln, i) => {
            const kk = interpolate(f, [8 + i * 6, 20 + i * 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.calm });
            return (
              <div key={i} style={{ fontFamily: FONT.serif, fontStyle: "italic", fontSize: size, lineHeight: 1.1, color: palette.ink,
                letterSpacing: "-0.01em", opacity: kk }}>{ln}</div>
            );
          })}
        </div>
        {who ? <div style={{ marginTop: 22, fontFamily: FONT.sans, fontWeight: 500, fontSize: v ? 30 : 26, color: "#4A4A48" }}>{who}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------------- Takeover
// The one spent moment: a phrase takes the frame after a short void. Words land on
// their spoken frames (`at` in seconds relative to the overlay start).
export const Takeover: React.FC<Base & { t0: number; words: { text: string; at: number; serif?: boolean; accent?: boolean }[]; align?: "left" | "center"; dim?: number; size?: { v: number; h: number }; maxRight?: number }> = ({
  format, palette, dur, t0, words, align = "left", dim = 0.82, size: sizeP, maxRight,
}) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const v = isVertical(format);
  const safe = SAFE[format];
  const size0 = sizeP ? (v ? sizeP.v : sizeP.h) : v ? 148 : 128;
  const size = maxRight ? Math.min(size0, 84) : size0;
  const { o } = envelope(f, dur, 4, 8);
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <AbsoluteFill style={{ background: `rgba(10,10,10,${dim})` }} />
      <div style={{ position: "absolute", left: safe.x0, right: maxRight ? 1920 - maxRight : SAFE[format].x0, top: v ? 520 : 300, textAlign: align,
        fontFamily: FONT.sans, fontWeight: 800, fontSize: size, lineHeight: 0.95, letterSpacing: "-0.04em", color: palette.text }}>
        {words.map((w, i) => {
          const wf = f - Math.round((w.at - t0) * fps);
          const kk = interpolate(wf, [0, 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
          return (
            <span key={i} style={{ display: "inline-block", marginRight: "0.22em", opacity: kk, transform: `translateY(${(1 - kk) * 0.3 * size}px)`,
              fontFamily: w.serif ? FONT.serif : FONT.sans, fontStyle: w.serif ? "italic" : "normal", fontWeight: w.serif ? 400 : 800,
              fontSize: w.serif ? size * 1.1 : size, letterSpacing: w.serif ? "0" : undefined, color: w.accent ? palette.accent : palette.text }}>
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------------- Footnote
export const Footnote: React.FC<Base & { text: string }> = ({ format, palette, dur, text }) => {
  const f = useCurrentFrame();
  const v = isVertical(format);
  const safe = SAFE[format];
  const line = interpolate(f, [0, 8], [0, 1], { extrapolateRight: "clamp", easing: EASE.enter });
  const t = interpolate(f, [4, 13], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  const { o } = envelope(f, dur, 1, 6);
  return (
    <div style={{ position: "absolute", left: safe.x0, top: v ? 1500 - 34 - 24 : 1000, opacity: o }}>
      <div style={{ width: 120, height: HAIRLINE, background: palette.text, opacity: 0.6, transform: `scaleX(${line})`, transformOrigin: "left", marginBottom: 14 }} />
      <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: v ? 34 : 30, color: palette.text, opacity: 0.85 * t,
        transform: `translateY(${(1 - t) * 6}px)`, textShadow: SHADOW.body }}>{text}</div>
    </div>
  );
};

// ----------------------------------------------------------------- ProgressBar
export const ProgressBar: React.FC<{ format: Format; palette: Palette; progress: number }> = ({ format, palette, progress }) => {
  const v = isVertical(format);
  const safe = SAFE[format];
  return (
    <div style={{ position: "absolute", left: safe.x0, width: safe.x1 - safe.x0, top: v ? 150 : 36, height: v ? 6 : 4, borderRadius: 3,
      background: "rgba(244,241,234,.18)", overflow: "hidden" }}>
      <div style={{ width: `${progress * 100}%`, height: "100%", background: palette.accent, opacity: 0.9 }} />
    </div>
  );
};

// ----------------------------------------------------------------- EndCard
export const EndCard: React.FC<Base & { text: string; handle?: string }> = ({ format, palette, dur, text, handle }) => {
  const f = useCurrentFrame();
  const v = isVertical(format);
  const dim = interpolate(f, [0, 12], [0, 0.6], { extrapolateRight: "clamp", easing: EASE.calm });
  const t = interpolate(f, [4, 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  return (
    <AbsoluteFill style={{ background: `rgba(10,10,10,${dim})`, alignItems: "center", justifyContent: "center" }}>
      <div style={{ opacity: t, transform: `translateY(${(1 - t) * 8}px)`, textAlign: "center", maxWidth: v ? 900 : 1300 }}>
        <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: v ? 56 : 48, color: palette.text, letterSpacing: "-0.02em",
          lineHeight: 1.1, textWrap: "balance" }}>{text}</div>
        {handle ? <div style={{ marginTop: 18, fontFamily: FONT.sans, fontWeight: 500, fontSize: v ? 30 : 26, color: palette.text, opacity: 0.75 }}>{handle}</div> : null}
      </div>
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------------- ChapterCard
export const ChapterCard: React.FC<Base & { num?: string; title: string }> = ({ format, palette, dur, num, title }) => {
  const f = useCurrentFrame();
  const v = isVertical(format);
  const { k, o } = envelope(f, dur, 12, 8);
  return (
    <AbsoluteFill style={{ background: `rgba(10,10,10,${0.55 * o})` }}>
      <div style={{ position: "absolute", left: SAFE[format].x0, top: v ? 820 : 420, opacity: o }}>
        {num ? <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: v ? 40 : 36, color: palette.accent, fontVariantNumeric: "tabular-nums",
          clipPath: maskUp(k) }}>{num}</div> : null}
        <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: v ? 72 : 64, color: palette.text, letterSpacing: "-0.02em",
          clipPath: maskUp(k), transform: `translateY(${(1 - k) * 16}px)` }}>{title}</div>
      </div>
    </AbsoluteFill>
  );
};

// ----------------------------------------------------------------- NumberCallout
// A number that is the point: counts up to `value` and lands 1-2 frames before the
// spoken number ends (`land`, absolute edit seconds), then an accent underline draws.
export const NumberCallout: React.FC<Base & { t0: number; value: number; land: number; prefix?: string; suffix?: string; label?: string; decimals?: number; x?: number; y?: number }> = ({
  format, palette, dur, t0, value, land, prefix = "", suffix = "", label, decimals = 0, x, y,
}) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const v = isVertical(format);
  const size = v ? 200 : 170;
  const landF = Math.round((land - t0) * fps);
  const k = interpolate(f, [Math.max(0, landF - 24), landF], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  const line = interpolate(f, [landF, landF + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
  const { o } = envelope(f, dur, 6, 8);
  const n = (value * k).toFixed(decimals);
  return (
    <div style={{ position: "absolute", left: x ?? SAFE[format].x0, top: y ?? (v ? 360 : 200), opacity: o }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, fontFamily: FONT.sans, fontWeight: 800, fontSize: size,
        letterSpacing: "-0.04em", fontVariantNumeric: "tabular-nums", color: palette.text, textShadow: SHADOW.display, lineHeight: 1 }}>
        <span>{prefix}{n}</span>
        {suffix ? <span style={{ fontSize: size * 0.42, fontWeight: 600, letterSpacing: "-0.02em" }}>{suffix}</span> : null}
      </div>
      <div style={{ height: 3, background: palette.accent, transform: `scaleX(${line})`, transformOrigin: "left", marginTop: 10 }} />
      {label ? <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: v ? 32 : 28, color: palette.text, opacity: 0.75, marginTop: 12,
        textShadow: SHADOW.body }}>{label}</div> : null}
    </div>
  );
};
