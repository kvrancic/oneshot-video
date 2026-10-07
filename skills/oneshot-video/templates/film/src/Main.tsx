import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { Board, Burst, BuildTo, Film, Finish, Flash, KIT_FONTS, Label, Layer, loadFonts, MaskLines, planFromLocks, Seg, Sfx, Slam } from "./kit";
import { BEATS, T } from "./timing";

loadFonts(KIT_FONTS);

// A starter film: replace the scenes with the beat sheet's. It renders as-is, without footage,
// so the pipeline (render, master, layers) can be checked before any asset exists.
// Footage: <Shot src="footage/px_123.mp4" from={3} /> inside a Seg. Music: <Music src="audio/music_edit.wav" />.
const WORD = "ONESHOT";

const Plate: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill className="plate" style={{ background: `radial-gradient(ellipse at ${50 + Math.sin(frame / 40) * 12}% 40%, #23314f 0%, #0A0A0D 70%)` }} />
  );
};

const Board1: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = (s: number) => Math.round(s * fps);
  // every letter but the first locks on a beat; the hero letter locks on the hit
  const locks = WORD.split("").map((_, i) => (i === 0 ? f(T.hit) : f(BEATS[16 + i])));
  const plans = planFromLocks(WORD, locks, [f(T.board) + 3, f(T.board + 1.2)], [f(BEATS[10]), f(BEATS[13])]);
  if (frame < f(T.board) || frame >= f(T.payoff)) return null;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <Board frame={frame} word={WORD} plans={plans} w={130} label="NOW PLAYING" sub="FROM A BRIEF" />
    </AbsoluteFill>
  );
};

export const Main: React.FC<{ layer?: Layer }> = ({ layer = "full" }) => (
  <Film layer={layer} theme={{ accent: "#FF4D2E" }}>
    <Seg a={T.title} b={T.build} name="plate"><Plate /></Seg>
    <Seg a={T.title} b={T.board} name="Title">
      <AbsoluteFill style={{ justifyContent: "center", paddingLeft: 140 }}>
        <MaskLines lines={["Footage in.", "Film out."]} size={150} delay={4} />
        <div style={{ marginTop: 40 }}><Label chip="DEMO" text="A STARTER FILM" at={20} size={40} /></div>
      </AbsoluteFill>
    </Seg>
    <Seg a={T.build} b={T.payoff} name="Build">
      <BuildTo hit={T.hit - T.build} beats={BEATS.map((b) => b - T.build)} chargeFrom={0}><Plate /></BuildTo>
    </Seg>
    <Board1 />
    <Seg a={T.payoff} b={T.end} name="Payoff">
      <AbsoluteFill style={{ background: "#FF4D2E" }} />
      <Burst />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}><Slam text={WORD} size={260} /></AbsoluteFill>
      <Flash frames={5} peak={0.45} />
    </Seg>
    <Seg a={0} b={T.end} name="finish"><Finish /></Seg>
    {BEATS.slice(0, 4).map((b, i) => <Sfx key={i} at={b} src="tick.wav" vol={0.6} />)}
    <Sfx at={T.board - 0.2} src="whoosh-soft.wav" vol={0.5} />
    <Sfx at={T.hit - 1.6} src="riser.wav" vol={0.6} />
    <Sfx at={T.hit - 0.01} src="thud-soft.wav" vol={1} />
    <Sfx at={T.payoff - 0.01} src="thud-soft.wav" vol={0.8} />
  </Film>
);
