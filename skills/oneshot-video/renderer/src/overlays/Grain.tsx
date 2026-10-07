import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

// Fine film grain over the whole composite so graphics sit in the footage.
// Seeded per frame (deterministic); overlay blend at low opacity.
export const Grain: React.FC<{ amount: number }> = ({ amount }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: amount, pointerEvents: "none" }}>
      <svg width="100%" height="100%">
        <filter id={`g${frame % 8}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={frame % 97} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#g${frame % 8})`} />
      </svg>
    </AbsoluteFill>
  );
};
