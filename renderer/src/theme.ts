import { Easing } from "remotion";

// Design tokens. One sans (Inter), one voice-switch serif (Instrument Serif), a mono
// only for literal logs. Values follow references/captions.md and references/motion.md.

export const FONT = {
  sans: "Inter",
  serif: "Instrument Serif",
  mono: "Geist Mono",
};

export type PaletteName = "paper" | "slate" | "editorial" | "nightlab" | "mono";

export type Palette = {
  ground: string; // plate / card background on dark
  text: string; // text on footage
  ink: string; // text on paper
  paper: string;
  muted: string;
  accent: string; // accent on dark
  accentInk: string; // accent on paper
  hairline: string;
  cool: string; // second speaker, LEDGER
};

export const PALETTES: Record<PaletteName, Palette> = {
  paper: {
    ground: "#111111",
    text: "#F4F1EA",
    ink: "#111111",
    paper: "#F4F1EA",
    muted: "#A8A39A",
    accent: "#FF7A4D",
    accentInk: "#C2410C",
    hairline: "#D9D4CA",
    cool: "#CFD8E6",
  },
  slate: {
    ground: "#0E1116",
    text: "#FFFFFF",
    ink: "#0E1116",
    paper: "#FFFFFF",
    muted: "#98A2B3",
    accent: "#8AB4FF",
    accentInk: "#2F4AE0",
    hairline: "#232834",
    cool: "#CFD8E6",
  },
  editorial: {
    ground: "#1B1714",
    text: "#F2EAD8",
    ink: "#1B1714",
    paper: "#F2EAD8",
    muted: "#A8A39A",
    accent: "#E07A5F",
    accentInk: "#9E2A2B",
    hairline: "#C9A36A",
    cool: "#D5DCE4",
  },
  nightlab: {
    ground: "#0B0D10",
    text: "#E9ECEF",
    ink: "#0B0D10",
    paper: "#E9ECEF",
    muted: "#7D8793",
    accent: "#FFB23F",
    accentInk: "#9A5B00",
    hairline: "#232830",
    cool: "#CFD8E6",
  },
  mono: {
    ground: "#0A0A0A",
    text: "#FFFFFF",
    ink: "#0A0A0A",
    paper: "#FFFFFF",
    muted: "#9A9A9A",
    accent: "#FFFFFF",
    accentInk: "#0A0A0A",
    hairline: "#2A2A2A",
    cool: "#D8D8D8",
  },
};

export const EASE = {
  enter: Easing.bezier(0.16, 1, 0.3, 1),
  exit: Easing.bezier(0.7, 0, 0.84, 0),
  move: Easing.bezier(0.65, 0, 0.35, 1),
  calm: Easing.bezier(0.45, 0, 0.55, 1),
  premium: Easing.bezier(0.4, 0, 0.2, 1),
  confident: Easing.bezier(0.2, 0.7, 0.2, 1),
  power3: Easing.bezier(0.215, 0.61, 0.355, 1),
};

// Remotion springs: damping ratio >= 1 collapses to critical damping, so
// {damping: 200} means "no bounce" and stiffness alone sets the speed.
export const SPRING = {
  snap: { damping: 24, stiffness: 300, mass: 1 }, // 4.9% overshoot, ~11 f
  settle: { damping: 18, stiffness: 120, mass: 1 }, // 1.1% overshoot, ~16 f
  glide: { damping: 200, stiffness: 170, mass: 1 }, // critical, ~15 f
  box: { damping: 200, stiffness: 400, mass: 1 }, // critical, ~10 f
  soft: { damping: 200, stiffness: 60, mass: 1 }, // critical, ~26 f
};

export const SHADOW = {
  body: "0 1px 2px rgba(0,0,0,.45), 0 4px 16px rgba(0,0,0,.35)",
  display: "0 2px 4px rgba(0,0,0,.40), 0 8px 28px rgba(0,0,0,.30)",
  card: "0 20px 60px rgba(0,0,0,.35), 0 2px 6px rgba(0,0,0,.20)",
};

export type Format = "9x16" | "16x9" | "1x1" | "4x5";

export const DIMS: Record<Format, { w: number; h: number }> = {
  "9x16": { w: 1080, h: 1920 },
  "16x9": { w: 1920, h: 1080 },
  "1x1": { w: 1080, h: 1080 },
  "4x5": { w: 1080, h: 1350 },
};

// Safe areas that clear TikTok / Reels / Shorts chrome (9:16) and title-safe (16:9).
export const SAFE: Record<Format, { x0: number; x1: number; y0: number; y1: number; rightKeepOutBelow?: number; rightKeepOutX?: number }> = {
  "9x16": { x0: 72, x1: 1008, y0: 160, y1: 1520, rightKeepOutBelow: 1100, rightKeepOutX: 940 },
  "16x9": { x0: 96, x1: 1824, y0: 54, y1: 1026 },
  "1x1": { x0: 72, x1: 1008, y0: 72, y1: 1008 },
  "4x5": { x0: 72, x1: 1008, y0: 96, y1: 1254 },
};

export const RADIUS = 12;
export const HAIRLINE = 2;
export const DUR = { quick: 6, standard: 12, slow: 21 };

export const isVertical = (f: Format) => f === "9x16" || f === "4x5";
