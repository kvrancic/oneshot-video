// Caption presets. Sizes are for a 1080-wide vertical frame (v) and a 1920-wide
// horizontal frame (h); y is the baseline of the LAST line (blocks grow upward).
// See references/captions.md for when to use which.

export type Anim =
  | "chunk-pop" // whole chunk springs in (scale .92 -> 1, y 10 -> 0); VERDICT, PUNCH
  | "karaoke" // page visible, words brighten as spoken; LECTURE, INDEX
  | "word-rise" // each word fades up from its own timestamp; FIRESIDE
  | "word-etch" // each word fades in place, slow; EPIGRAPH, DUSK
  | "slide-side" // page slides in from the speaker's side; LEDGER
  | "box"; // one highlight box slides word to word; KARAOKE

export type Emphasis = "accent" | "serif" | "none";

export type Preset = {
  name: string;
  family: "sans" | "serif";
  weight: number;
  italic?: boolean;
  size: { v: number; h: number };
  lineHeight: number;
  tracking: number; // em
  textCase: "sentence" | "lower" | "asis";
  chunk: {
    maxWords: number;
    maxChars: number; // per line
    maxLines: number;
    combineMs: number; // target page duration
    breakOnSilenceMs: number;
  };
  y: { v: number; h: number; vSplit?: number };
  align: "center" | "left" | "speaker";
  unspokenOpacity: number; // 1 = no karaoke dimming
  scrim: false | { bg: string; radius: number; padX: number; padY: number };
  shadow: "body" | "display" | "soft";
  anim: Anim;
  emphasis: Emphasis;
  emphasisScale: number;
  activeUnderline?: boolean;
  leadMs: number; // page appears this early
  holdMs: number; // page lingers after its last word
  exitFrames: number;
  clearOnPauseMs?: number;
  boxColor?: "accent" | "text";
};

export const PRESETS: Record<string, Preset> = {
  // Hot takes, contrarian claims, hooks. Hormozi's mechanics without the noise.
  verdict: {
    name: "VERDICT",
    family: "sans",
    weight: 800,
    size: { v: 76, h: 62 },
    lineHeight: 1.04,
    tracking: -0.025,
    textCase: "sentence",
    chunk: { maxWords: 3, maxChars: 16, maxLines: 2, combineMs: 550, breakOnSilenceMs: 180 },
    y: { v: 1380, h: 960, vSplit: 1500 },
    align: "center",
    unspokenOpacity: 1,
    scrim: false,
    shadow: "display",
    anim: "chunk-pop",
    emphasis: "accent",
    emphasisScale: 1.06,
    leadMs: 100,
    holdMs: 250,
    exitFrames: 4,
  },
  // Explainers and lecture excerpts: a calm rail where every word is readable.
  lecture: {
    name: "LECTURE",
    family: "sans",
    weight: 600,
    size: { v: 58, h: 48 },
    lineHeight: 1.18,
    tracking: -0.005,
    textCase: "sentence",
    chunk: { maxWords: 7, maxChars: 28, maxLines: 2, combineMs: 1400, breakOnSilenceMs: 300 },
    y: { v: 1400, h: 984, vSplit: 1500 },
    align: "center",
    unspokenOpacity: 0.6,
    scrim: { bg: "rgba(10,10,10,.5)", radius: 14, padX: 22, padY: 12 },
    shadow: "body",
    anim: "karaoke",
    emphasis: "accent",
    emphasisScale: 1,
    activeUnderline: false,
    leadMs: 100,
    holdMs: 600,
    exitFrames: 5,
  },
  // Stories: warm, intimate; one serif word as the image.
  fireside: {
    name: "FIRESIDE",
    family: "sans",
    weight: 500,
    size: { v: 62, h: 50 },
    lineHeight: 1.12,
    tracking: -0.01,
    textCase: "sentence",
    chunk: { maxWords: 5, maxChars: 26, maxLines: 2, combineMs: 1100, breakOnSilenceMs: 250 },
    y: { v: 1360, h: 960, vSplit: 1500 },
    align: "center",
    unspokenOpacity: 0,
    scrim: false,
    shadow: "body",
    anim: "word-rise",
    emphasis: "serif",
    emphasisScale: 1.15,
    leadMs: 80,
    holdMs: 600,
    exitFrames: 8,
  },
  // Lists: the rail plus an item heading (the heading is an overlay: ListHeading).
  index: {
    name: "INDEX",
    family: "sans",
    weight: 600,
    size: { v: 60, h: 48 },
    lineHeight: 1.18,
    tracking: -0.005,
    textCase: "sentence",
    chunk: { maxWords: 7, maxChars: 28, maxLines: 2, combineMs: 1400, breakOnSilenceMs: 300 },
    y: { v: 1400, h: 984, vSplit: 1500 },
    align: "center",
    unspokenOpacity: 0.55,
    scrim: { bg: "rgba(10,10,10,.38)", radius: 14, padX: 22, padY: 12 },
    shadow: "body",
    anim: "karaoke",
    emphasis: "accent",
    emphasisScale: 1,
    leadMs: 100,
    holdMs: 600,
    exitFrames: 5,
  },
  // Reading a quote: serif carries the quoted words, words etch in.
  epigraph: {
    name: "EPIGRAPH",
    family: "serif",
    weight: 400,
    italic: true,
    size: { v: 72, h: 56 },
    lineHeight: 1.1,
    tracking: -0.01,
    textCase: "asis",
    chunk: { maxWords: 9, maxChars: 30, maxLines: 3, combineMs: 2000, breakOnSilenceMs: 450 },
    y: { v: 1400, h: 980, vSplit: 1500 },
    align: "center",
    unspokenOpacity: 0,
    scrim: false,
    shadow: "soft",
    anim: "word-etch",
    emphasis: "none",
    emphasisScale: 1,
    leadMs: 60,
    holdMs: 800,
    exitFrames: 10,
  },
  // Debate and contrast between two speakers: position and temperature code the speaker.
  ledger: {
    name: "LEDGER",
    family: "sans",
    weight: 600,
    size: { v: 60, h: 50 },
    lineHeight: 1.12,
    tracking: -0.01,
    textCase: "sentence",
    chunk: { maxWords: 5, maxChars: 24, maxLines: 2, combineMs: 1200, breakOnSilenceMs: 250 },
    y: { v: 1380, h: 984, vSplit: 1500 },
    align: "speaker",
    unspokenOpacity: 1,
    scrim: false,
    shadow: "body",
    anim: "slide-side",
    emphasis: "accent",
    emphasisScale: 1,
    leadMs: 100,
    holdMs: 500,
    exitFrames: 6,
  },
  // Calm and reflective: lowercase, slow subtitle, no emphasis colour.
  dusk: {
    name: "DUSK",
    family: "sans",
    weight: 500,
    size: { v: 54, h: 44 },
    lineHeight: 1.25,
    tracking: 0,
    textCase: "lower",
    chunk: { maxWords: 8, maxChars: 34, maxLines: 2, combineMs: 2200, breakOnSilenceMs: 400 },
    y: { v: 1440, h: 990, vSplit: 1500 },
    align: "center",
    unspokenOpacity: 0,
    scrim: false,
    shadow: "soft",
    anim: "word-etch",
    emphasis: "serif",
    emphasisScale: 1.12,
    leadMs: 60,
    holdMs: 700,
    exitFrames: 12,
    clearOnPauseMs: 1500,
  },
  // Energetic but premium: one box glides from word to word on a critically damped spring.
  karaoke: {
    name: "KARAOKE",
    family: "sans",
    weight: 700,
    size: { v: 64, h: 52 },
    lineHeight: 1.16,
    tracking: -0.015,
    textCase: "sentence",
    chunk: { maxWords: 5, maxChars: 22, maxLines: 2, combineMs: 1200, breakOnSilenceMs: 280 },
    y: { v: 1390, h: 980, vSplit: 1500 },
    align: "center",
    unspokenOpacity: 0.9,
    scrim: false,
    shadow: "body",
    anim: "box",
    emphasis: "none",
    emphasisScale: 1,
    leadMs: 100,
    holdMs: 450,
    exitFrames: 5,
    boxColor: "accent",
  },
  // Loud but not cheap: two-word punches, heavy weight, one accent word, snap spring.
  punch: {
    name: "PUNCH",
    family: "sans",
    weight: 900,
    size: { v: 92, h: 72 },
    lineHeight: 0.98,
    tracking: -0.035,
    textCase: "sentence",
    chunk: { maxWords: 2, maxChars: 12, maxLines: 2, combineMs: 420, breakOnSilenceMs: 160 },
    y: { v: 1340, h: 950, vSplit: 1500 },
    align: "center",
    unspokenOpacity: 1,
    scrim: false,
    shadow: "display",
    anim: "chunk-pop",
    emphasis: "accent",
    emphasisScale: 1.08,
    leadMs: 100,
    holdMs: 200,
    exitFrames: 3,
  },
};

export const presetFor = (name: string): Preset => {
  const p = PRESETS[name.toLowerCase()];
  if (!p) {
    throw new Error(`Unknown caption preset "${name}". Known: ${Object.keys(PRESETS).join(", ")}`);
  }
  return p;
};
