import { interpolate } from "remotion";
import { EASE } from "../theme";

// Entrance and exit envelope for an overlay living `dur` frames (local frame f).
export const envelope = (f: number, dur: number, inF = 12, outF = 8) => {
  const k = interpolate(f, [0, inF], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.enter });
  const o = interpolate(f, [dur - outF, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.exit });
  return { k, o, alpha: Math.min(k, o) };
};

export const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

// Mask reveal from the bottom edge up: pass k in 0..1.
export const maskUp = (k: number) => `inset(${(1 - k) * 100}% 0 0 0)`;
