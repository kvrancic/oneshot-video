import { Audio } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Sequence, staticFile, useVideoConfig } from "remotion";
import { DEFAULT_THEME, KitTheme, ThemeContext } from "./theme";

// One composition renders the finished film or a single editable layer of it, so the same code
// that made the film hands it to Premiere / Final Cut / Resolve frame for frame (scripts/film_layers.py).
// plates: footage only (anything with className="plate"); graphics: everything else on alpha;
// music / sfx / voice: one audio stem each.
export type Layer = "full" | "plates" | "graphics" | "music" | "sfx" | "voice";
export const LayerContext = React.createContext<Layer>("full");
export const useLayer = () => React.useContext(LayerContext);
export const hears = (layer: Layer, stem: "music" | "sfx" | "voice") => layer === "full" || layer === stem;

const LAYER_CSS = `.layer-plates * { visibility: hidden; } .layer-plates .plate, .layer-plates .plate * { visibility: visible; }
.layer-graphics .plate { visibility: hidden; }`;

// The root of every film: theme, layer and the background that the graphics layer leaves transparent.
export const Film: React.FC<{ layer?: Layer; theme?: Partial<KitTheme>; children: React.ReactNode }> = ({ layer = "full", theme, children }) => (
  <ThemeContext.Provider value={{ ...DEFAULT_THEME, ...theme }}>
    <LayerContext.Provider value={layer}>
      <AbsoluteFill className={`layer-${layer}`} style={{ background: layer === "graphics" ? "transparent" : "#000" }}>
        <style>{LAYER_CSS}</style>
        {children}
      </AbsoluteFill>
    </LayerContext.Provider>
  </ThemeContext.Provider>
);

// A scene from second a to second b (film time). Name it: the name becomes the clip name on V2.
export const Seg: React.FC<{ a: number; b: number; name?: string; children: React.ReactNode }> = ({ a, b, name, children }) => {
  const { fps } = useVideoConfig();
  const from = Math.round(a * fps);
  return <Sequence from={from} durationInFrames={Math.max(1, Math.round(b * fps) - from)} name={name}>{children}</Sequence>;
};

// A sound effect at second `at` (film time), from public/sfx/ unless src has a folder.
export const Sfx: React.FC<{ at: number; src: string; vol?: number; dur?: number }> = ({ at, src, vol = 0.6, dur }) => {
  const layer = useLayer();
  const { fps } = useVideoConfig();
  if (!hears(layer, "sfx")) return null;
  return (
    <Sequence from={Math.max(0, Math.round(at * fps))} durationInFrames={dur ? Math.round(dur * fps) : undefined} layout="none">
      <Audio src={staticFile(src.includes("/") ? src : `sfx/${src}`)} volume={vol} />
    </Sequence>
  );
};

// The music bed (public/ path). volume may be a function of the frame for ducks and lifts.
export const Music: React.FC<{ src: string; volume?: number | ((frame: number) => number) }> = ({ src, volume = 0.9 }) => {
  const layer = useLayer();
  if (!hears(layer, "music")) return null;
  return <Audio src={staticFile(src)} volume={volume} />;
};
