// Every time in the film, in seconds of film time, in one place. Derive scene starts from the beat
// grid (beats.json from scripts/beats.py) and verified lyric or voice times, never by eye in the
// components; then a music edit moves everything together.
// SCENES and SHOTS name the cuts for the editor hand-back (V2 per scene, V1 per shot); MARKERS become markers.
export const FPS = 30;
export const W = 1920;
export const H = 1080;

const beat = 60 / 120; // replace with beats.json once the music is chosen
const B = Array.from({ length: 64 }, (_, i) => i * beat);

export const T = {
  title: B[0],
  board: B[6],
  build: B[14],
  hit: B[22], // the impact: the hero letter is settled on this frame
  payoff: B[24], // the cut to the payoff card, a beat or two after the hit
  end: B[30],
  total: B[30] + 0.8, // let the last boom ring out over black
};

export const BEATS = B;

export const SCENES: [number, number, string][] = [
  [T.title, T.board, "Title"],
  [T.board, T.build, "Board"],
  [T.build, T.payoff, "Build"],
  [T.payoff, T.end, "Payoff"],
  [T.end, T.total, "Black"],
];

export const SHOTS: [number, number, string][] = [[T.title, T.end, "plate"]];

export const MARKERS: [number, string][] = [[T.hit, "hit"]];
