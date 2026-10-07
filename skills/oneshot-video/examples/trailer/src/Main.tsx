import { Video } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Easing, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Board, Burst, BuildTo, Film, Finish, Flash, KIT_FONTS, Label, Layer, loadFonts, MaskLines, Music, planFromLocks, Seg, Sfx, Shot, Slam, useTheme } from "./kit";
import { BEATS, T } from "./timing";

loadFonts(KIT_FONTS);

const ACCENT = "#FF4D2E";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const out = Easing.bezier(0.16, 1, 0.3, 1);

const Plate: React.FC = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill className="plate" style={{ background: `radial-gradient(ellipse at ${50 + Math.sin(frame / 50) * 14}% 35%, #1d2a45 0%, #0A0A0D 70%)` }} />;
};

const Kicker: React.FC<{ n: string; mode: string; line: string }> = ({ n, mode, line }) => (
  <div style={{ position: "absolute", left: 120, top: 96 }}>
    <Label chip={`MODE ${n}`} text={mode} size={34} />
    <div style={{ marginTop: 28 }}><MaskLines lines={[line]} size={64} font="serif" delay={6} /></div>
  </div>
);

// Three phones rise in on the beat, each playing a finished clip.
const Phone: React.FC<{ src: string; i: number }> = ({ src, i }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [8 + i * 15, 24 + i * 15], [0, 1], { ...clamp, easing: out });
  return (
    <div className="plate" style={{ width: 390, height: 693, borderRadius: 40, overflow: "hidden", border: "6px solid #1b1b20",
      boxShadow: "0 30px 80px rgba(0,0,0,.6)", transform: `translateY(${(1 - p) * 700}px) rotate(${(1 - p) * (i - 1) * 6}deg)`, opacity: p }}>
      <Video src={staticFile(`footage/${src}`)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </div>
  );
};

const Clips: React.FC = () => (
  <AbsoluteFill>
    <Plate />
    <Kicker n="01" mode="CLIPS" line="A 25-minute speech in. Clips that stand alone out." />
    <AbsoluteFill style={{ flexDirection: "row", gap: 44, justifyContent: "flex-end", alignItems: "flex-end", paddingBottom: 60, paddingRight: 110 }}>
      <Phone src="clip1.mp4" i={0} />
      <Phone src="clip2.mp4" i={1} />
      <Phone src="clip3.mp4" i={2} />
    </AbsoluteFill>
  </AbsoluteFill>
);

// A timeline: fillers and dead air (red) drop out and the shots close up, then it ships to the editors.
const SHOT_W = [210, 70, 160, 50, 240, 90, 180, 60, 200, 140];
const CUT = [false, true, false, true, false, true, false, true, false, false];
const CAM = ["A", "", "B", "", "SCREEN", "", "A", "", "B", "A"];
const Timeline: React.FC = () => {
  const frame = useCurrentFrame();
  const th = useTheme();
  const k = interpolate(frame, [40, 85], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  const ship = interpolate(frame, [110, 130], [0, 1], { ...clamp, easing: out });
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
          <rect x={s.x} y={y} width={s.w} height={h} rx={6} fill={kind === "g" ? "#F5D90A" : color(s.i)} opacity={kind === "a" ? 0.55 : 0.9} />
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
    <AbsoluteFill>
      <Plate />
      <Kicker n="02" mode="FULL EDIT" line="Fillers and dead air out. The best angle on every sentence." />
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        <g transform="translate(240, 430) scale(1.12)">
          {track(0, "V2", 48, "g")}
          {track(64, "V1", 90, "v")}
          {track(170, "A1", 90, "a")}
        </g>
      </svg>
      <div style={{ position: "absolute", left: 280, top: 860, display: "flex", gap: 22, opacity: ship, transform: `translateY(${(1 - ship) * 30}px)` }}>
        {["PREMIERE PRO", "FINAL CUT PRO", "DAVINCI RESOLVE"].map((n) => (
          <div key={n} style={{ fontFamily: th.mono, fontWeight: 700, fontSize: 28, letterSpacing: "0.12em", color: "#fff", padding: "14px 22px", border: "2px solid rgba(255,255,255,.35)", borderRadius: 10 }}>{n}</div>
        ))}
        <div style={{ fontFamily: th.mono, fontSize: 26, color: "rgba(255,255,255,.6)", alignSelf: "center", marginLeft: 8 }}>← the timeline, on your original media</div>
      </div>
    </AbsoluteFill>
  );
};

const Scratch: React.FC = () => {
  const { fps } = useVideoConfig();
  const f = (s: number) => Math.round(s * fps);
  return (
    <AbsoluteFill>
      <Seg a={0} b={2.6} name="map"><Shot src="footage/reveal_map.mp4" zoom={[1, 1.04]} /></Seg>
      <Seg a={2.6} b={6} name="board"><Shot src="footage/reveal_board.mp4" from={1.6} zoom={[1, 1.05]} /></Seg>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,.72) 0%, rgba(0,0,0,0) 34%)" }} />
      <Kicker n="03" mode="FROM SCRATCH" line="A 6-second clip, a song and a logo became this opener." />
      <Seg a={0} b={0.2}><Flash frames={f(0.2)} peak={0.35} /></Seg>
    </AbsoluteFill>
  );
};

const WORD = "ONESHOT";
const BoardLayer: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = (s: number) => Math.round(s * fps);
  if (frame < f(T.build) || frame >= f(T.hit) + 1) return null;
  // the other letters lock on quarter beats into the hit; the hero O locks on the hit itself
  const locks = WORD.split("").map((_, i) => (i === 0 ? f(T.hit) : f(T.build + 0.5 + (i - 1) * 0.25)));
  const plans = planFromLocks(WORD, locks, [f(T.build), f(T.build + 0.4)]);
  const enter = interpolate(frame, [f(T.build), f(T.build) + 8], [0.85, 1], { ...clamp, easing: out });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ transform: `scale(${enter * 1.25})` }}><Board frame={frame} word={WORD} plans={plans} w={150} label="NOW PLAYING" sub="YOUR NEXT VIDEO" /></div>
    </AbsoluteFill>
  );
};

const Payoff: React.FC = () => {
  const th = useTheme();
  const frame = useCurrentFrame();
  const sub = interpolate(frame, [18, 30], [0, 1], { ...clamp, easing: out });
  return (
    <AbsoluteFill style={{ background: ACCENT }}>
      <Burst colors={["#FFFFFF", "#0A0A0D"]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 40 }}>
        <Slam text="oneshot-video" size={180} font="display" overshoot={1.12} />
        <div style={{ opacity: sub, transform: `translateY(${(1 - sub) * 20}px)`, textAlign: "center" }}>
          <div style={{ fontFamily: th.serif, fontStyle: "italic", fontSize: 64, color: "#fff" }}>Your agent is now a video editor.</div>
          <div style={{ marginTop: 26, fontFamily: th.mono, fontWeight: 600, fontSize: 30, letterSpacing: "0.16em", color: "rgba(255,255,255,.9)" }}>CLAUDE CODE · CODEX · CURSOR · LOCAL ON YOUR MAC</div>
          <div style={{ marginTop: 18, fontFamily: th.mono, fontSize: 30, letterSpacing: "0.06em", color: "#0A0A0D" }}>github.com/kvrancic/oneshot-video</div>
        </div>
      </AbsoluteFill>
      <Flash frames={5} peak={0.4} />
    </AbsoluteFill>
  );
};

export const Main: React.FC<{ layer?: Layer }> = ({ layer = "full" }) => (
  <Film layer={layer} theme={{ accent: ACCENT }}>
    <Seg a={T.title} b={T.clips} name="Title">
      <Plate />
      <AbsoluteFill style={{ justifyContent: "center", paddingLeft: 140 }}>
        <div style={{ marginBottom: 40 }}><Label chip="OPEN SOURCE" text="ONESHOT-VIDEO" at={6} size={36} /></div>
        <MaskLines lines={["Your agent is", "now a video editor."]} size={150} delay={12} stagger={8} />
      </AbsoluteFill>
    </Seg>
    <Seg a={T.clips} b={T.edit} name="Clips"><Clips /></Seg>
    <Seg a={T.edit} b={T.scratch} name="Full edit"><Timeline /></Seg>
    <Seg a={T.scratch} b={T.build} name="From scratch"><Scratch /></Seg>
    <Seg a={T.build} b={T.hit} name="Build">
      <BuildTo hit={T.hit - T.build} beats={BEATS.map((b) => b - T.build)} chargeFrom={0}><Plate /></BuildTo>
    </Seg>
    <BoardLayer />
    <Seg a={T.hit} b={T.end} name="Payoff"><Payoff /></Seg>
    <Seg a={T.end} b={T.total} name="Black"><AbsoluteFill style={{ background: "#000" }} /></Seg>
    <Seg a={0} b={T.end} name="finish"><Finish grain={0.06} /></Seg>
    <Music src="audio/groove.wav" volume={0.9} />
    <Sfx at={T.clips - 0.15} src="whoosh-soft.wav" vol={0.35} />
    <Sfx at={T.edit - 0.15} src="whoosh-soft.wav" vol={0.35} />
    <Sfx at={T.scratch - 0.15} src="whoosh-long.wav" vol={0.35} />
    {[0, 1, 2, 3, 4, 5].map((i) => <Sfx key={i} at={T.build + 0.5 + i * 0.25} src="tick.wav" vol={0.5} />)}
  </Film>
);
