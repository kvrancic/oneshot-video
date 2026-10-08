import { Video } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { hears, useLayer } from "./layers";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// A vertical (9:16) video shown properly in a landscape film: full height, centred (or at x), over a
// blurred, zoomed copy of itself, so the clip reads as itself (captions, graphics, framing) instead of a
// thumbnail. Enters with a short zoom punch. volume > 0 plays its own sound (on the voice stem).
export const Vertical: React.FC<{ src: string; from?: number; x?: number; volume?: number; punch?: boolean; radius?: number }> = ({ src, from = 0, x, volume = 0, punch = true, radius = 28 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const layer = useLayer();
  const h = height * 0.94, w = h * 9 / 16;
  const s = punch ? interpolate(frame, [0, 6, 12], [1.12, 0.985, 1], { ...clamp, easing: Easing.out(Easing.cubic) }) : 1;
  const left = (x ?? width / 2) - w / 2;
  const vol = hears(layer, "voice") ? volume : 0;
  const trim = Math.round(from * fps);
  return (
    <AbsoluteFill className="plate" style={{ background: "#000", overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: "scale(1.25)", filter: "blur(38px) brightness(0.45) saturate(1.3)" }}>
        <Video src={staticFile(src)} muted trimBefore={trim} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      <div style={{ position: "absolute", left, top: (height - h) / 2, width: w, height: h, borderRadius: radius, overflow: "hidden",
        transform: `scale(${s})`, boxShadow: "0 40px 120px rgba(0,0,0,.7)" }}>
        <Video src={staticFile(src)} muted={vol === 0} volume={vol} trimBefore={trim} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </div>
    </AbsoluteFill>
  );
};

// A whip: the scene slides in from one side with horizontal motion blur over a few frames. Wrap a
// scene's content in it at the start of its Seg; cut on the beat.
export const Whip: React.FC<{ from?: "left" | "right" | "up"; frames?: number; children: React.ReactNode }> = ({ from = "right", frames = 7, children }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const p = interpolate(frame, [0, frames], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const d = (1 - p) * (from === "up" ? height : width) * 0.6 * (from === "left" ? -1 : 1);
  const blur = (1 - p) * 40;
  const t = from === "up" ? `translateY(${d}px)` : `translateX(${d}px)`;
  return <AbsoluteFill style={{ transform: t, filter: blur > 0.5 ? `blur(${from === "up" ? 0 : blur}px)` : undefined }}>{children}</AbsoluteFill>;
};
