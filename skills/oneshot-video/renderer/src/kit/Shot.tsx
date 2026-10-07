import { Video } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// One footage shot, graded, with a slow push so nothing ever sits still (a locked frame reads as a
// stalled player). src is a public/ path ("footage/px_123.mp4"); from is seconds into the source.
export const Shot: React.FC<{
  src: string;
  from?: number;
  zoom?: [number, number];
  x?: [number, number]; // pan, % of the frame
  y?: [number, number];
  grade?: string; // CSS filter
  rate?: number;
  dim?: number; // extra darkening 0..1, for text over bright plates
  volume?: number; // 0 = muted (default); the clip's own sound goes to the voice stem
}> = ({ src, from = 0, zoom = [1.04, 1.14], x = [0, 0], y = [0, 0], grade, rate = 1, dim = 0, volume = 0 }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const e = Easing.out(Easing.quad)(interpolate(frame, [0, durationInFrames], [0, 1], { extrapolateRight: "clamp" }));
  const s = zoom[0] + (zoom[1] - zoom[0]) * e;
  const tx = x[0] + (x[1] - x[0]) * e;
  const ty = y[0] + (y[1] - y[0]) * e;
  return (
    <AbsoluteFill className="plate" style={{ overflow: "hidden", background: "#000" }}>
      <AbsoluteFill style={{ transform: `translate(${tx}%, ${ty}%) scale(${s})`, filter: grade ?? "contrast(1.12) saturate(1.12) brightness(0.98)" }}>
        <Video src={staticFile(src)} muted={volume === 0} volume={volume} trimBefore={Math.round(from * fps)} playbackRate={rate}
          style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </AbsoluteFill>
      {dim > 0 && <AbsoluteFill style={{ background: `rgba(5,5,10,${dim})` }} />}
    </AbsoluteFill>
  );
};

// Film finish over everything: vignette and moving grain.
export const Finish: React.FC<{ vignette?: number; grain?: number }> = ({ vignette = 0.45, grain = 0.09 }) => {
  const seed = useCurrentFrame() % 7;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,${vignette}) 100%)` }} />
      {grain > 0 && (
        <svg className="plate" width="100%" height="100%" style={{ position: "absolute", opacity: grain, mixBlendMode: "overlay" }}>
          <filter id={`grain${seed}`}>
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={seed} stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="100%" height="100%" filter={`url(#grain${seed})`} />
        </svg>
      )}
    </AbsoluteFill>
  );
};

// A flash that decays over a few frames: a cut accent. Never over a wrong letter or a face mid-blink.
export const Flash: React.FC<{ frames?: number; color?: string; peak?: number }> = ({ frames = 6, color = "#fff", peak = 0.9 }) => {
  const o = interpolate(useCurrentFrame(), [0, frames], [peak, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return <AbsoluteFill style={{ background: color, opacity: o, mixBlendMode: "screen", pointerEvents: "none" }} />;
};
