import { Audio } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Easing, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import {
  Board, Burst, BuildTo, Film, Finish, Flash, hears, KIT_FONTS, Label, Layer, loadFonts, MaskLines, planFromLocks, Seg, Sfx, Shot, Slam,
  useLayer, useTheme, Vertical, Whip,
} from "./kit";
import { BEATS, T } from "./timing";

loadFonts(KIT_FONTS);

const ACCENT = "#FF4D2E";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const out = Easing.bezier(0.16, 1, 0.3, 1);

const Plate: React.FC = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill className="plate" style={{ background: `radial-gradient(ellipse at ${50 + Math.sin(frame / 40) * 16}% 35%, #22325a 0%, #0A0A0D 70%)` }} />;
};

// A feature called out beside the vertical clip: an accent chip and a two-line label that slides in.
const Callout: React.FC<{ side: "left" | "right"; chip: string; lines: string[]; at?: number }> = ({ side, chip, lines, at = 6 }) => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const p = interpolate(frame, [at, at + 10], [0, 1], { ...clamp, easing: out });
  const pos = side === "left" ? { left: 110 } : { right: 110 };
  return (
    <div style={{ position: "absolute", top: 380, width: 520, ...pos, textAlign: side === "left" ? "left" : "right",
      opacity: p, transform: `translateX(${(1 - p) * (side === "left" ? -60 : 60)}px)` }}>
      <span style={{ background: th.accent, color: "#fff", fontFamily: th.mono, fontWeight: 700, fontSize: 30, letterSpacing: "0.14em", padding: "8px 14px" }}>{chip}</span>
      <div style={{ marginTop: 22 }}><MaskLines lines={lines} size={72} delay={at + 2} stagger={4} align={side === "left" ? "left" : "left"} /></div>
    </div>
  );
};

const ClipScene: React.FC<{ src: string; n: string; chip: string; lines: string[]; side: "left" | "right"; whip: "left" | "right" | "up" }> = ({ src, n, chip, lines, side, whip }) => (
  <Whip from={whip}>
    <Vertical src={`footage/${src}`} volume={1} x={side === "left" ? 1920 - 560 : 560} />
    <Callout side={side} chip={chip} lines={lines} />
    <div style={{ position: "absolute", [side === "left" ? "left" : "right"]: 110, top: 96 }}><Label chip={`MODE ${n}`} text="CLIPS" size={34} at={0} /></div>
    <Flash frames={4} peak={0.25} />
  </Whip>
);

// The full edit as a timeline: fillers (red) drop out, the shots close up, then it ships to the editors.
const SHOT_W = [220, 70, 170, 50, 250, 90, 190, 60, 210, 150];
const CUT = [false, true, false, true, false, true, false, true, false, false];
const CAM = ["A", "", "B", "", "SCREEN", "", "A", "", "B", "A"];
const Timeline: React.FC = () => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const k = interpolate(frame, [10, 34], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const ship = interpolate(frame, [36, 48], [0, 1], { ...clamp, easing: out });
  let x = 0;
  const shots = SHOT_W.map((w, i) => {
    const ww = CUT[i] ? w * (1 - k) : w;
    const el = { x, w: ww, i };
    x += ww + (ww > 0.5 ? 6 : 0);
    return el;
  });
  const color = (i: number) => (CUT[i] ? "#E5484D" : CAM[i] === "SCREEN" ? "#3E63DD" : CAM[i] === "B" ? "#8E4EC6" : "#12A594");
  const track = (y: number, label: string, h: number, kind: "v" | "a" | "g") => (
    <g>
      <text x={-24} y={y + h / 2 + 8} textAnchor="end" fill="rgba(255,255,255,.6)" fontFamily={th.mono} fontSize={22}>{label}</text>
      {shots.map((s) => s.w > 0.5 && (kind !== "g" || s.i % 4 === 0) && (
        <g key={s.i}>
          <rect x={s.x} y={y} width={s.w} height={h} rx={6} fill={kind === "g" ? "#F5D90A" : color(s.i)} opacity={kind === "a" ? 0.55 : 0.92} />
          {kind === "a" && Array.from({ length: Math.floor(s.w / 9) }, (_, j) => (
            <rect key={j} x={s.x + 4 + j * 9} y={y + h / 2 - (6 + ((j * 37 + s.i * 11) % 22))} width={4} height={2 * (6 + ((j * 37 + s.i * 11) % 22))} fill="rgba(255,255,255,.75)" />
          ))}
          {kind === "v" && CAM[s.i] && s.w > 60 && <text x={s.x + 12} y={y + 34} fill="#fff" fontFamily={th.mono} fontSize={20} fontWeight={700}>{CAM[s.i]}</text>}
          {kind === "v" && CUT[s.i] && k < 0.3 && <text x={s.x + 8} y={y + 34} fill="#fff" fontFamily={th.mono} fontSize={18}>UM</text>}
        </g>
      ))}
    </g>
  );
  return (
    <Whip from="up">
      <Plate />
      <div style={{ position: "absolute", left: 120, top: 96 }}>
        <Label chip="MODE 02" text="FULL EDIT" size={34} />
        <div style={{ marginTop: 26 }}><MaskLines lines={["Fillers out.", "Best angle. Every sentence."]} size={84} delay={3} /></div>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        <g transform="translate(200, 470) scale(1.16)">
          {track(0, "V2", 48, "g")}
          {track(64, "V1", 90, "v")}
          {track(170, "A1", 90, "a")}
        </g>
      </svg>
      <div style={{ position: "absolute", left: 200, top: 880, display: "flex", gap: 22 }}>
        {["PREMIERE PRO", "FINAL CUT PRO", "DAVINCI RESOLVE"].map((n, i) => {
          const p = interpolate(frame, [36 + i * 3, 46 + i * 3], [0, 1], { ...clamp, easing: out });
          return <div key={n} style={{ opacity: p, transform: `translateY(${(1 - p) * 40}px) scale(${0.9 + 0.1 * p})`, fontFamily: th.mono, fontWeight: 700, fontSize: 32, letterSpacing: "0.12em", color: "#fff", padding: "16px 24px", border: `3px solid ${i === 0 ? th.accent : "rgba(255,255,255,.4)"}`, borderRadius: 12 }}>{n}</div>;
        })}
        <div style={{ opacity: ship, fontFamily: th.mono, fontSize: 28, color: "rgba(255,255,255,.7)", alignSelf: "center", marginLeft: 6 }}>← an editable timeline</div>
      </div>
    </Whip>
  );
};

// The Boston opener, full screen, with its own song: the board locking BOSTON, then its impact.
const Scratch: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const th = useTheme();
  const layer = useLayer();
  const lab = interpolate(frame, [4, 14, 70, 80], [0, 1, 1, 0], clamp);
  const a = T.scratch2 - T.scratch;
  return (
    <AbsoluteFill>
      <Seg a={0} b={a} name="opener: board"><Whip from="right"><Shot src="footage/reveal_a.mp4" zoom={[1, 1.03]} grade="none" volume={hears(layer, "voice") ? 1 : 0} /></Whip></Seg>
      <Seg a={a} b={T.build - T.scratch} name="opener: impact"><Shot src="footage/reveal_b.mp4" zoom={[1.02, 1.06]} grade="none" volume={hears(layer, "voice") ? 1 : 0} /><Flash frames={5} peak={0.5} /></Seg>
      <AbsoluteFill style={{ background: "linear-gradient(0deg, rgba(0,0,0,.85) 0%, rgba(0,0,0,.5) 22%, rgba(0,0,0,0) 36%)", opacity: lab }} />
      <div style={{ position: "absolute", left: 110, bottom: 64, right: 110, opacity: lab, display: "flex", alignItems: "flex-end", gap: 40 }}>
        <Label chip="MODE 03" text="FROM SCRATCH" size={32} />
        <div>
          <MaskLines lines={["A 6-second clip, a song and a logo became this."]} size={58} delay={6} font="serif" />
          <div style={{ marginTop: 14, fontFamily: th.mono, fontSize: 24, color: "rgba(255,255,255,.8)", letterSpacing: "0.1em" }}>MUSIC EDIT · 20 STOCK SHOTS · MOTION GRAPHICS · ONE CONVERSATION</div>
        </div>
      </div>
      <Sequence from={Math.round(a * fps)} durationInFrames={2} layout="none"><Flash frames={2} peak={0.6} /></Sequence>
    </AbsoluteFill>
  );
};

const WORD = "ONESHOT";
const BoardLayer: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = (s: number) => Math.round(s * fps);
  if (frame < f(T.build) || frame >= f(T.hit) + 1) return null;
  const locks = WORD.split("").map((_, i) => (i === 0 ? f(T.hit) : f(T.build + 0.47 + (i - 1) * 0.2)));
  const plans = planFromLocks(WORD, locks, [f(T.build), f(T.build + 0.35)]);
  const enter = interpolate(frame, [f(T.build), f(T.build) + 6], [0.8, 1], { ...clamp, easing: out });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ transform: `scale(${enter * 1.3})` }}><Board frame={frame} word={WORD} plans={plans} w={150} label="NOW PLAYING" sub="YOUR NEXT VIDEO" /></div>
    </AbsoluteFill>
  );
};

const Title: React.FC = () => {
  const { fps } = useVideoConfig();
  const b = (n: number) => Math.round(n * (60 / 128) * fps);
  return (
    <AbsoluteFill>
      <Plate />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 10 }}>
        <Slam text="Footage in." size={190} at={0} />
        <Slam text="Film out." size={190} at={b(2)} color={ACCENT} />
      </AbsoluteFill>
      <Flash frames={4} peak={0.5} />
    </AbsoluteFill>
  );
};

const Payoff: React.FC = () => {
  const th = useTheme();
  const frame = useCurrentFrame();
  const sub = interpolate(frame, [14, 26], [0, 1], { ...clamp, easing: out });
  return (
    <AbsoluteFill style={{ background: ACCENT }}>
      <Burst colors={["#FFFFFF", "#0A0A0D"]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 40 }}>
        <Slam text="oneshot-video" size={180} overshoot={1.12} />
        <div style={{ opacity: sub, transform: `translateY(${(1 - sub) * 20}px)`, textAlign: "center" }}>
          <div style={{ fontFamily: th.serif, fontStyle: "italic", fontSize: 68, color: "#fff" }}>Your agent is now a video editor.</div>
          <div style={{ marginTop: 26, fontFamily: th.mono, fontWeight: 600, fontSize: 30, letterSpacing: "0.16em", color: "rgba(255,255,255,.92)" }}>CLAUDE CODE · CODEX · CURSOR · LOCAL ON YOUR MAC</div>
          <div style={{ marginTop: 18, fontFamily: th.mono, fontWeight: 700, fontSize: 34, letterSpacing: "0.05em", color: "#0A0A0D" }}>github.com/kvrancic/oneshot-video</div>
        </div>
      </AbsoluteFill>
      <Flash frames={5} peak={0.4} />
    </AbsoluteFill>
  );
};

// Music: under the clips it ducks so their voices come through; silent while the opener plays its song.
const musicVolume = (fps: number) => (frame: number) => {
  const t = frame / fps;
  if (t >= T.scratch - 0.05 && t < T.build) return 0;
  if ((t >= T.clips + 0.25 && t < T.edit) || t < T.title) return 0.28;
  return 0.95;
};

export const Main: React.FC<{ layer?: Layer }> = ({ layer = "full" }) => {
  const { fps } = useVideoConfig();
  return (
    <Film layer={layer} theme={{ accent: ACCENT }}>
      <Seg a={T.cold} b={T.title} name="Cold open"><Vertical src="footage/cold.mp4" volume={1} /></Seg>
      <Seg a={T.title} b={T.clips} name="Title"><Title /></Seg>
      <Seg a={T.clips} b={T.clip2} name="Clip 1"><ClipScene src="clipA.mp4" n="01" chip="TEXT BEHIND" lines={["The word goes", "behind the", "speaker."]} side="right" whip="up" /></Seg>
      <Seg a={T.clip2} b={T.clip3} name="Clip 2"><ClipScene src="clipB.mp4" n="01" chip="COUNT-UPS" lines={["Numbers land", "on the word", "she says."]} side="left" whip="right" /></Seg>
      <Seg a={T.clip3} b={T.edit} name="Clip 3"><ClipScene src="clipC.mp4" n="01" chip="VIRTUAL CAMERA" lines={["16:9 in.", "9:16 out.", "It follows him."]} side="right" whip="left" /></Seg>
      <Seg a={T.edit} b={T.scratch} name="Full edit"><Timeline /></Seg>
      <Seg a={T.scratch} b={T.build} name="From scratch"><Scratch /></Seg>
      <Seg a={T.build} b={T.hit} name="Build"><BuildTo hit={T.hit - T.build} beats={BEATS.map((b) => b - T.build)} chargeFrom={0}><Plate /></BuildTo></Seg>
      <BoardLayer />
      <Seg a={T.hit} b={T.end} name="Payoff"><Payoff /></Seg>
      <Seg a={T.end} b={T.total} name="Black"><AbsoluteFill style={{ background: "#000" }} /></Seg>
      <Seg a={0} b={T.end} name="finish"><Finish grain={0.05} vignette={0.35} /></Seg>
      {hears(layer, "music") && <Audio src={staticFile("audio/groove128.wav")} volume={musicVolume(fps)} />}
      {[T.clips, T.clip2, T.clip3, T.edit, T.scratch].map((t, i) => <Sfx key={i} at={t - 0.12} src="whoosh-soft.wav" vol={0.45} />)}
      {[0, 1, 2, 3, 4, 5].map((i) => <Sfx key={`t${i}`} at={T.build + 0.47 + i * 0.2} src="tick.wav" vol={0.55} />)}
    </Film>
  );
};
