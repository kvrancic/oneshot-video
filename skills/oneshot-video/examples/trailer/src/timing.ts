// The oneshot-video trailer. 128 BPM chiptune (tools/chip.py): a beat every 0.469 s, a bar every 1.875 s.
// Scenes start on bars except where the speaker's own words set the cut.
export const FPS = 30;
export const W = 1920;
export const H = 1080;

export const BEAT = 60 / 128;
export const BAR = 4 * BEAT;
const bar = (n: number) => n * BAR;
const beat = (n: number) => n * BEAT;

export const T = {
  hook: 0, // "Who says AI video can't be edited in" + three empty editor windows
  windows: bar(1), // 1.875: the windows pop in, one per beat
  drop: bar(2), // 3.75: the timelines fill
  title: bar(3), // 5.625: ONESHOT-VIDEO
  raw: bar(4), // 7.5: the raw phone recording, his voice: "I don't feel creative dragging clips on Adobe Premiere for 10 hours."
  wipe: bar(5), // 9.375: pixel wipe from the raw recording to the edit, same sentence
  ai: 11.7, // "AI takes it off my hands," in the edit's pixel scene
  zap: 13.6, // the robot zaps the stumbles the edit removed
  long: bar(9), // 16.875: dive into the stage, then the long form
  longCuts: bar(10), // 18.75: four shots of the edit, two beats each
  short: bar(12), // 22.5: the long form folds into a phone
  shorts: bar(12) + beat(2), // 23.44: three vertical clips
  scratch: bar(16), // 30.0: no footage at all? the Boston opener
  reveal: bar(16) + beat(2),
  idea: bar(18), // 33.75: "The idea becomes a machine that makes the art."
  logo: bar(20), // 37.5
  total: 40.0,
};

export const ZAPS = [0, 1, 2, 3, 4, 5].map((i) => T.zap + 0.46 + beat(i));
export const SHORT_SLOTS = [0, 1, 2].map((i) => T.shorts + i * ((T.scratch - T.shorts) / 3));

export const SCENES: [number, number, string][] = [
  [T.hook, T.drop, "Hook"],
  [T.drop, T.title, "Timelines"],
  [T.title, T.raw, "Title"],
  [T.raw, T.ai, "Raw to edit"],
  [T.ai, T.zap, "AI takes it"],
  [T.zap, T.long, "Stumbles"],
  [T.long, T.short, "Long form"],
  [T.short, T.scratch, "Short form"],
  [T.scratch, T.idea, "From scratch"],
  [T.idea, T.logo, "The idea"],
  [T.logo, T.total, "Logo"],
];
export const SHOTS = SCENES;
export const MARKERS: [number, string][] = [[T.drop, "drop"], [T.long, "long form"], [T.short, "short form"], [T.scratch, "from scratch"]];
