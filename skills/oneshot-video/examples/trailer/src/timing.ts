// The oneshot-video trailer. 120 BPM: a beat every 0.5 s, a bar every 2 s.
export const FPS = 30;
export const W = 1920;
export const H = 1080;

export const BEATS = Array.from({ length: 66 }, (_, i) => i * 0.5);
const bar = (n: number) => n * 2;

export const T = {
  title: 0,
  clips: bar(2), // 4.0
  edit: bar(6), // 12.0
  scratch: bar(9), // 18.0
  build: bar(12), // 24.0
  hit: bar(13), // 26.0: the board's O locks, the payoff lands
  end: 31.0,
  total: 32.0,
};

export const SCENES: [number, number, string][] = [
  [T.title, T.clips, "Title"],
  [T.clips, T.edit, "Clips"],
  [T.edit, T.scratch, "Full edit"],
  [T.scratch, T.build, "From scratch"],
  [T.build, T.hit, "Build"],
  [T.hit, T.end, "Payoff"],
  [T.end, T.total, "Black"],
];

export const SHOTS: [number, number, string][] = [
  [T.clips, T.edit, "clips: Sandberg, UC Berkeley 2016 (CC BY 3.0)"],
  [T.scratch, T.build, "Boston reveal excerpts"],
];

export const MARKERS: [number, string][] = [[T.hit, "hit"]];
