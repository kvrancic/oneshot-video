import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { Label } from "./Type";
import { useTheme } from "./theme";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const io = Easing.bezier(0.65, 0, 0.35, 1);

type Pt = { x: number; y: number; label?: string };

// A route across a map: a close-up on the origin, pull out to the whole map while the route draws,
// then an exponential dive into the destination that keeps it on screen the whole way (a linear zoom
// throws the target off the edge). Map paths come from scripts/mapsvg.py (projected to 1920x1080).
// Frames are relative to the Seg: [0, out] pull out, [draw0, draw1] route, [dive0, dive1] dive.
export const RouteMap: React.FC<{
  paths: Record<string, string>;
  from: Pt;
  to: Pt;
  highlight?: string; // a region that floods with the accent on arrival
  hideTo?: boolean; // keep the destination's name a mystery ("? ? ?")
  overview?: { x: number; y: number; s: number };
  timing?: { out: number; draw0: number; draw1: number; dive0: number; dive1: number };
  arcLift?: number; // how far the route bows upward, px; keep it inside the frame
  diveScale?: number;
  chip?: string;
  caption?: string;
  ground?: string;
}> = ({ paths, from: S, to: D, highlight, hideTo, overview = { x: 960, y: 540, s: 0.9 }, timing = { out: 26, draw0: 12, draw1: 64, dive0: 64, dive1: 99 },
  arcLift = 110, diveScale = 5.2, chip, caption, ground = "#0B1422" }) => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const mid = { x: (S.x + D.x) / 2, y: Math.min(S.y, D.y) - arcLift };
  const quad = (t: number) => ({
    x: (1 - t) ** 2 * S.x + 2 * (1 - t) * t * mid.x + t ** 2 * D.x,
    y: (1 - t) ** 2 * S.y + 2 * (1 - t) * t * mid.y + t ** 2 * D.y,
  });
  const k1 = interpolate(frame, [0, timing.out], [0, 1], { ...clamp, easing: io });
  const k2 = interpolate(frame, [timing.dive0, timing.dive1], [0, 1], { ...clamp, easing: Easing.in(Easing.cubic) });
  const c0 = { x: S.x + 120, y: S.y + 120, s: 2.6 }, c1 = overview;
  let cx = c0.x + (c1.x - c0.x) * k1, cy = c0.y + (c1.y - c0.y) * k1, s = c0.s + (c1.s - c0.s) * k1;
  if (k2 > 0) {
    const p1 = { x: 960 + (D.x - c1.x) * c1.s, y: 540 + (D.y - c1.y) * c1.s };
    s = c1.s * Math.pow(diveScale / c1.s, k2);
    const px = p1.x + (960 - p1.x) * k2, py = p1.y + (560 - p1.y) * k2;
    cx = D.x - (px - 960) / s;
    cy = D.y - (py - 540) / s;
  }
  const t = interpolate(frame, [timing.draw0, timing.draw1], [0, 1], { ...clamp, easing: io });
  const pts = Array.from({ length: 81 }, (_, i) => quad((i / 80) * t));
  const d = "M" + pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join("L");
  const head = quad(t);
  const arrived = frame >= timing.draw1;
  const ring = arrived ? (frame - timing.draw1) / 16 : 0;
  const flood = arrived ? interpolate(frame, [timing.draw1, timing.draw1 + 12], [0, 1], clamp) : 0;
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 60% 40%, #13213a 0%, ${ground} 70%)`, overflow: "hidden" }}>
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        <defs>
          <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.4" fill="rgba(255,255,255,.06)" /></pattern>
          <filter id="glow"><feGaussianBlur stdDeviation="6" /></filter>
        </defs>
        <rect width="1920" height="1080" fill="url(#dots)" />
        <g transform={`translate(${960 - cx * s},${540 - cy * s}) scale(${s})`}>
          {Object.entries(paths).map(([name, p]) => (
            <path key={name} d={p} fill="#16223a" stroke="rgba(255,255,255,.22)" strokeWidth={1.2 / s} strokeLinejoin="round" />
          ))}
          {highlight && paths[highlight] && flood > 0 && (
            <path d={paths[highlight]} fill={th.accent} fillOpacity={0.92 * flood} stroke={th.accent} strokeWidth={1.2 / s} strokeLinejoin="round" />
          )}
          <path d={d} fill="none" stroke={th.accent} strokeWidth={10 / s} opacity={0.35} filter="url(#glow)" />
          <path d={d} fill="none" stroke={th.accent} strokeWidth={4 / s} strokeLinecap="round" />
          <path d={d} fill="none" stroke="#fff" strokeWidth={1.4 / s} strokeDasharray={`${6 / s} ${10 / s}`} />
          <circle cx={S.x} cy={S.y} r={7 / s} fill="#fff" />
          <circle cx={S.x} cy={S.y} r={(14 + (frame % 20)) / s} fill="none" stroke="#fff" strokeWidth={1.5 / s} opacity={1 - (frame % 20) / 20} />
          {S.label && <text x={S.x + 16 / s} y={S.y + 30 / s} fill="#fff" fontFamily={th.mono} fontWeight={700} fontSize={20 / s} letterSpacing={3 / s}>{S.label}</text>}
          {!arrived && <circle cx={head.x} cy={head.y} r={9 / s} fill="#fff" stroke={th.accent} strokeWidth={4 / s} />}
          {arrived && (
            <g>
              <circle cx={D.x} cy={D.y} r={8 / s} fill="#fff" />
              {[0, 0.5].map((o) => {
                const r = (ring + o) % 1;
                return <circle key={o} cx={D.x} cy={D.y} r={(10 + r * 60) / s} fill="none" stroke={th.accent} strokeWidth={3 / s} opacity={1 - r} />;
              })}
              {(D.label || hideTo) && <text x={D.x - 150 / s} y={D.y - 22 / s} fill="#fff" fontFamily={th.mono} fontWeight={700} fontSize={26 / s} letterSpacing={4 / s}>
                {hideTo ? (D.label ?? "???").replace(/\S/g, "? ").trim() : D.label}</text>}
            </g>
          )}
        </g>
      </svg>
      {caption && <div style={{ position: "absolute", left: 120, bottom: 120 }}><Label chip={chip} text={caption} at={10} size={40} /></div>}
    </AbsoluteFill>
  );
};
