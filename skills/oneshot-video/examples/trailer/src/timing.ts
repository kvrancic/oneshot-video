// The oneshot-video trailer. 128 BPM: a beat every 0.469 s, a bar every 1.875 s. Every scene starts on a bar.
export const FPS = 30;
export const W = 1920;
export const H = 1080;

export const BEAT = 60 / 128;
export const BAR = 4 * BEAT;
export const BEATS = Array.from({ length: 80 }, (_, i) => i * BEAT);
const bar = (n: number) => n * BAR;

export const T = {
  cold: 0, // a clip's big moment, full height, with its sound: two bars
  title: bar(2), // 3.75: "Footage in. Film out." slams, a roll into the drop
  clips: bar(3), // 5.625: the drop; three clips, two bars each
  clip2: bar(5),
  clip3: bar(7),
  edit: bar(9), // 16.875: the timeline
  scratch: bar(11), // 20.625: the Boston opener with its own song
  scratch2: bar(11) + 5.75,
  build: bar(15), // 28.125: the board
  hit: bar(16), // 30.0: ONESHOT locks, the payoff
  end: 33.1,
  total: 34.0,
};

export const SCENES: [number, number, string][] = [
  [T.cold, T.title, "Cold open"],
  [T.title, T.clips, "Title"],
  [T.clips, T.clip2, "Clip 1"],
  [T.clip2, T.clip3, "Clip 2"],
  [T.clip3, T.edit, "Clip 3"],
  [T.edit, T.scratch, "Full edit"],
  [T.scratch, T.build, "From scratch"],
  [T.build, T.hit, "Build"],
  [T.hit, T.end, "Payoff"],
  [T.end, T.total, "Black"],
];
export const SHOTS = SCENES;
export const MARKERS: [number, string][] = [[T.clips, "drop"], [T.hit, "hit"]];
