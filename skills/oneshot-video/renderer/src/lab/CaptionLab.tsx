import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { Captions } from "../captions/Captions";
import type { Token } from "../captions/layout";
import { Format, PALETTES, PaletteName } from "../theme";
import { useFontsReady } from "../useFonts";

export type CaptionLabProps = { preset: string; format: Format; palette: PaletteName; tokens: Token[] };

export const CaptionLab: React.FC<CaptionLabProps> = ({ preset, format, palette, tokens }) => {
  const ready = useFontsReady();
  const bg = format === "16x9" ? "lab/bg169.jpg" : "lab/bg916.jpg";
  const starts = tokens.map((t, i) => (i === 0 || /[.!?]$/.test(tokens[i - 1].text) ? i : -1)).filter((i) => i >= 0);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Img src={staticFile(bg)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      {ready ? (
        <Captions tokens={tokens} preset={preset} format={format} palette={PALETTES[palette]} sentenceStarts={starts} />
      ) : null}
    </AbsoluteFill>
  );
};
