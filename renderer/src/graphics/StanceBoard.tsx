import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { EASE, FONT, Palette, SPRING } from "../theme";

// A board that introduces people one by one and places each on a stance axis, then
// reveals a pattern by colouring every chip by group. Built for "who thinks what"
// montages (for example AI leaders on AGI). All times are edit seconds, absolute.

export type Person = {
  id: string;
  name: string;
  role: string;
  photo?: string;
  x: number; // 0 (left label) .. 1 (right label)
  group?: string; // matched against reveal.groups
  at: number; // introduced
  row?: -1 | 1; // above (-1) or below (1) the axis; default alternates
  stance?: string; // one line, the speaker's words
  note?: { text: string; at: number }; // a second line that lands later
  years?: { values: string[]; at: number[]; label?: string }; // stamped, then struck through
};

export type StanceBoardProps = {
  title?: string;
  axis: { left: string; right: string };
  people: Person[];
  // Each group's label lands when the speaker names that group (`at`); people whose
  // group is not listed stay neutral between the clusters (no claim is made about them).
  reveal?: { at: number; title?: string; groups: Record<string, { label: string; color?: "accent" | "cool"; at?: number }> };
};

type Box = { w: number; h: number; palette: Palette; t0: number; vertical: boolean };

const Chip: React.FC<{ p: Person; size: number; ring: string; ringW: number; gray: number }> = ({ p, size, ring, ringW, gray }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size / 2,
      overflow: "hidden",
      boxShadow: `0 0 0 ${ringW}px ${ring}, 0 10px 30px rgba(0,0,0,.35)`,
      background: "#1A1A1A",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    {p.photo ? (
      <Img src={staticFile(p.photo)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: `grayscale(${gray}) contrast(1.05)` }} />
    ) : (
      <span style={{ fontFamily: FONT.sans, fontWeight: 600, fontSize: size * 0.36, color: "#F4F1EA" }}>
        {p.name.split(" ").map((s) => s[0]).join("")}
      </span>
    )}
  </div>
);

export const StanceBoard: React.FC<StanceBoardProps & Box> = ({ title, axis, people, reveal, w, h, palette, t0, vertical }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = t0 + frame / fps; // absolute edit seconds
  const F = (s: number) => Math.round((s - t0) * fps); // absolute seconds -> local frame

  const introduced = people.filter((p) => t >= p.at - 0.1);
  const current = introduced[introduced.length - 1];
  const revealK = reveal
    ? interpolate(frame, [F(reveal.at), F(reveal.at) + 24], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move })
    : 0;

  const pad = vertical ? 56 : 48;
  const chip = vertical ? 108 : 92;
  const axisY = vertical ? h - 250 : h - 230;
  const axisX0 = pad + chip * 0.55;
  const axisX1 = w - pad - chip * 0.55;
  const bigChip = chip * (1 + 0.25 * revealK);

  // Card for the current person.
  const card = (p: Person, idx: number) => {
    const next = introduced[idx + 1];
    const fIn = frame - F(p.at - 0.1);
    const kIn = interpolate(fIn, [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
    const kOut = next ? interpolate(frame - F(next.at - 0.1), [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.exit }) : 0;
    const alpha = kIn * (1 - kOut) * (1 - revealK);
    if (alpha <= 0.001) return null;
    const portrait = vertical ? 268 : 230;
    const photoK = spring({ frame: fIn, fps, config: SPRING.settle });
    const stanceK = interpolate(fIn, [8, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
    const noteK = p.note ? interpolate(frame - F(p.note.at), [0, 14], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter }) : 0;
    return (
      <div key={p.id} style={{ position: "absolute", left: pad, right: pad, top: vertical ? 96 : 70, opacity: alpha,
        transform: `translateY(${(1 - kIn) * 24 - kOut * 18}px)`, display: "flex", gap: vertical ? 40 : 36, alignItems: "flex-start" }}>
        <div style={{ transform: `scale(${0.9 + 0.1 * photoK})`, transformOrigin: "50% 50%", flexShrink: 0 }}>
          <Chip p={p} size={portrait} ring={palette.accent} ringW={3} gray={0.15} />
        </div>
        <div style={{ paddingTop: 14, minWidth: 0 }}>
          <div style={{ fontFamily: FONT.sans, fontWeight: 700, fontSize: vertical ? 70 : 60, letterSpacing: "-0.03em", color: palette.text, lineHeight: 1.02 }}>{p.name}</div>
          <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: vertical ? 32 : 28, color: palette.muted, marginTop: 10 }}>{p.role}</div>
          {p.stance ? (
            <div style={{ fontFamily: FONT.serif, fontStyle: "italic", fontSize: vertical ? 52 : 44, lineHeight: 1.06, color: palette.text,
              marginTop: 24, opacity: stanceK, transform: `translateY(${(1 - stanceK) * 10}px)`, textWrap: "balance" }}>{p.stance}</div>
          ) : null}
          {p.note ? (
            <div style={{ fontFamily: FONT.sans, fontWeight: 600, fontSize: vertical ? 32 : 28, color: palette.accent, marginTop: 16, lineHeight: 1.2,
              opacity: noteK, transform: `translateY(${(1 - noteK) * 8}px)` }}>{p.note.text}</div>
          ) : null}
          {p.years ? (
            <div style={{ marginTop: 18 }}>
              {p.years.label ? <div style={{ fontFamily: FONT.sans, fontWeight: 500, fontSize: vertical ? 30 : 28, color: palette.muted, marginBottom: 4 }}>{p.years.label}</div> : null}
              <div style={{ display: "flex", gap: 22, alignItems: "baseline" }}>
              {p.years.values.map((y, i) => {
                const f0 = F(p.years!.at[i]);
                const s = spring({ frame: frame - f0, fps, config: SPRING.snap });
                const nextAt = p.years!.at[i + 1] ?? p.years!.at[i] + 1.2;
                const strike = interpolate(frame, [F(nextAt) - 2, F(nextAt) + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
                if (frame < f0) return null;
                return (
                  <span key={y} style={{ position: "relative", fontFamily: FONT.sans, fontWeight: 800, fontSize: vertical ? 50 : 44,
                    fontVariantNumeric: "tabular-nums", letterSpacing: "-0.03em", color: palette.text,
                    opacity: Math.min(1, s * 1.4) * (1 - 0.45 * strike), transform: `scale(${0.85 + 0.15 * s})`, display: "inline-block" }}>
                    {y}
                    <span style={{ position: "absolute", left: -4, right: -4, top: "54%", height: 5, background: palette.accent,
                      transform: `scaleX(${strike})`, transformOrigin: "left", borderRadius: 3 }} />
                  </span>
                );
              })}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    );
  };

  // The board opens on its own (a big heading and the empty axis), so the panel is never
  // blank while the speaker leads in; the heading shrinks to a label when the first person lands.
  const axisK = interpolate(frame, [6, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
  const firstIn = interpolate(frame, [F(people[0].at) - 8, F(people[0].at) + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
  const headIn = interpolate(frame, [2, 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });

  // Chip rows: alternate above and below the axis to avoid collisions. On the reveal,
  // chips leave the axis and regroup into one cluster per group.
  const groups = reveal ? Object.keys(reveal.groups) : [];
  const clusterSlot = (p: Person) => {
    const gi = groups.indexOf(p.group ?? "");
    const members = people.filter((q) => q.group === p.group).sort((a, b) => a.x - b.x);
    const idx = members.findIndex((q) => q.id === p.id);
    const cols = Math.min(members.length, 2);
    const rows = Math.ceil(members.length / cols);
    const colW = chip * 1.5;
    const cx = gi === 0 ? w * 0.24 : w * 0.76;
    const col = idx % cols;
    const row = Math.floor(idx / cols);
    const lastRowCount = members.length - (rows - 1) * cols;
    const rowCols = row === rows - 1 ? lastRowCount : cols;
    const x = cx + (col - (rowCols - 1) / 2) * colW;
    const y = (vertical ? h * 0.45 : h * 0.44) + (row - (rows - 1) / 2) * chip * 1.35;
    return { x, y };
  };
  const placed = introduced.map((p, i) => {
    const fIn = frame - F(p.at);
    const s = spring({ frame: fIn, fps, config: SPRING.settle });
    const ax = axisX0 + (axisX1 - axisX0) * Math.min(0.97, Math.max(0.03, p.x));
    const row = p.row ?? (i % 2 === 0 ? -1 : 1);
    const ay = axisY + row * (chip * 0.5 + 30);
    const inGroup = !!(reveal && p.group && reveal.groups[p.group]);
    // Someone the pattern does not fit sits apart: centred, lower, smaller, no colour.
    const slot = inGroup ? clusterSlot(p) : reveal ? { x: w / 2, y: (vertical ? h * 0.45 : h * 0.44) + chip * 0.95 } : { x: ax, y: ay };
    const stagger = interpolate(frame, [F(reveal?.at ?? 1e9) + i * 2, F(reveal?.at ?? 1e9) + i * 2 + 26], [0, 1], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
    return { p, x: ax + (slot.x - ax) * stagger, y: ay + (slot.y - ay) * stagger, s, row, neutral: !!reveal && !inGroup };
  });

  const groupColor = (g?: string) => {
    if (!reveal || !g || !reveal.groups[g]) return palette.muted;
    const c = reveal.groups[g]?.color ?? "accent";
    return c === "accent" ? palette.accent : palette.cool;
  };

  return (
    <div style={{ position: "absolute", inset: 0, width: w, height: h }}>
      {title ? (
        <div style={{ position: "absolute", left: pad, right: pad, top: (vertical ? 30 : 20) + (1 - firstIn) * (vertical ? 170 : 150),
          fontFamily: FONT.sans, fontWeight: firstIn > 0.5 ? 600 : 700, fontSize: (vertical ? 30 : 28) + (1 - firstIn) * (vertical ? 46 : 36),
          letterSpacing: firstIn > 0.5 ? "0.02em" : "-0.03em", lineHeight: 1.05, color: firstIn > 0.5 ? palette.muted : palette.text,
          opacity: headIn * (1 - revealK), transform: `translateY(${(1 - headIn) * 16}px)` }}>{title}</div>
      ) : null}
      {reveal?.title ? (
        <div style={{ position: "absolute", left: pad, right: pad, top: vertical ? 70 : 50, fontFamily: FONT.sans, fontWeight: 800,
          fontSize: vertical ? 72 : 64, letterSpacing: "-0.035em", lineHeight: 1, color: palette.text, opacity: revealK,
          transform: `translateY(${(1 - revealK) * 16}px)` }}>{reveal.title}</div>
      ) : null}
      {introduced.map((p, i) => card(p, i))}

      {/* axis */}
      <div style={{ position: "absolute", left: axisX0, width: (axisX1 - axisX0) * axisK, top: axisY - 1, height: 2, background: palette.text, opacity: 0.4 * (1 - revealK) }} />
      {[0, 0.25, 0.5, 0.75, 1].map((k) => (
        <div key={k} style={{ position: "absolute", left: axisX0 + (axisX1 - axisX0) * k - 1, top: axisY - 7, width: 2, height: 14, background: palette.text,
          opacity: 0.35 * axisK * (1 - revealK) }} />
      ))}
      <div style={{ position: "absolute", left: axisX0 - chip * 0.4, top: axisY + chip + 58, fontFamily: FONT.sans, fontWeight: 500, fontSize: vertical ? 30 : 26,
        color: palette.muted, opacity: axisK * (1 - revealK) }}>← {axis.left}</div>
      <div style={{ position: "absolute", right: w - axisX1 - chip * 0.4, top: axisY + chip + 58, fontFamily: FONT.sans, fontWeight: 500, fontSize: vertical ? 30 : 26,
        color: palette.muted, opacity: axisK * (1 - revealK), textAlign: "right" }}>{axis.right} →</div>

      {placed.map(({ p, x, y, s, neutral }) => {
        const isCur = current && current.id === p.id && revealK < 0.5;
        const ring = revealK > 0 ? (neutral ? "rgba(244,241,234,.35)" : groupColor(p.group)) : isCur ? palette.accent : "rgba(244,241,234,.35)";
        const size = isCur ? chip * 1.12 : neutral ? chip * (1 - 0.2 * revealK) : bigChip;
        return (
          <div key={p.id} style={{ position: "absolute", left: x - size / 2, top: y - size / 2 - (1 - s) * 60, opacity: Math.min(1, s * 1.3) }}>
            <Chip p={p} size={size} ring={ring} ringW={isCur || (revealK > 0 && !neutral) ? 4 : 2} gray={isCur ? 0 : neutral ? 1 : 1 - revealK * 0.7} />
          </div>
        );
      })}

      {reveal
        ? Object.entries(reveal.groups).map(([g, spec], gi) => {
            const members = people.filter((q) => q.group === g);
            if (!members.length) return null;
            const slots = members.map(clusterSlot);
            const cx = gi === 0 ? w * 0.24 : w * 0.76;
            const bottom = Math.max(...slots.map((q) => q.y)) + bigChip / 2 + 28;
            const la = F(spec.at ?? reveal.at) + (spec.at ? 0 : 20 + gi * 8);
            const k = interpolate(frame, [la, la + 16], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
            return (
              <div key={g} style={{ position: "absolute", left: cx - 230, width: 460, textAlign: "center", top: bottom, opacity: k, transform: `translateY(${(1 - k) * 10}px)` }}>
                <div style={{ fontFamily: FONT.serif, fontStyle: "italic", fontSize: vertical ? 54 : 46, lineHeight: 1.05, color: spec.color === "cool" ? palette.cool : palette.accent }}>{spec.label}</div>
              </div>
            );
          })
        : null}
    </div>
  );
};
