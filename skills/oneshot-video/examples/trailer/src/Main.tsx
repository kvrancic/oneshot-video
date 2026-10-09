import { Audio, Video } from "@remotion/media";
import React from "react";
import { AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Film, FontFaceSpec, hears, Layer, loadFonts, Seg, Sfx, useLayer } from "./kit";
import { BEAT, SHORT_SLOTS, T, ZAPS } from "./timing";

// The look borrows the language of the Seattle talk's own graphics: Jersey 10 (the face of its chapter
// cards), the deck's pixel sprites, a navy grid, hard shadows, motion on twos.
const FONTS: FontFaceSpec[] = [
  ["Jersey", "fonts/Jersey10-Regular.ttf", "400", "normal", "100%"],
  ["Silk", "fonts/Silkscreen-Bold.ttf", "700", "normal", "100%"],
];
loadFonts(FONTS);

const C = { navy: "#15122B", grid: "#26224A", ink: "#0B0918", cyan: "#3FE0F0", yellow: "#FFD23F", orange: "#FF6B2C", red: "#E8384F", white: "#F6F1E6", green: "#5BE37D", purple: "#9B7BFF" };
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const twos = (f: number) => Math.floor(f / 2) * 2; // animate on twos: chunky, hand-made motion
const fr = (s: number) => Math.round(s * 30);
const shadow = (d: number, c = C.ink) => Array.from({ length: d }, (_, i) => `${i + 1}px ${i + 1}px 0 ${c}`).join(",");

const Grid: React.FC<{ tint?: string }> = ({ tint = C.navy }) => (
  <AbsoluteFill style={{ background: tint, backgroundImage: `linear-gradient(${C.grid} 2px, transparent 2px), linear-gradient(90deg, ${C.grid} 2px, transparent 2px)`, backgroundSize: "60px 60px" }} />
);

// Pixel type: Jersey 10, a hard stepped shadow, stamped in over 3 frames.
const Px: React.FC<{ children: React.ReactNode; size: number; color?: string; at?: number; depth?: number; style?: React.CSSProperties; stamp?: boolean }> = ({ children, size, color = C.white, at = 0, depth, style, stamp = true }) => {
  const f = useCurrentFrame() - at;
  if (f < 0) return null;
  const s = stamp ? [1.5, 1.22, 1.06, 1][Math.min(3, f)] : 1;
  return (
    <div style={{ fontFamily: "Jersey", fontSize: size * 1.1, lineHeight: 0.88, color, textShadow: shadow(depth ?? Math.max(5, Math.round(size / 16))), transform: `scale(${s})`, whiteSpace: "pre", ...style }}>{children}</div>
  );
};

const Sprite: React.FC<{ name: string; h: number; x: number; y: number; at?: number; bob?: boolean; flip?: boolean; enter?: "up" | "left" | "right" | "pop" }> = ({ name, h, x, y, at = 0, bob = true, flip, enter = "pop" }) => {
  const f = useCurrentFrame() - at;
  if (f < 0) return null;
  const p = Math.min(1, twos(f) / 8);
  const off = enter === "up" ? [0, (1 - p) * 300] : enter === "left" ? [-(1 - p) * 500, 0] : enter === "right" ? [(1 - p) * 500, 0] : [0, 0];
  const sc = enter === "pop" ? [0.2, 0.7, 1.15, 1][Math.min(3, Math.floor(f / 2))] : 1;
  const b = bob && Math.floor(f / 8) % 2 ? -6 : 0;
  return (
    <Img src={staticFile(`sprites/${name}.png`)} style={{ position: "absolute", left: x + off[0], top: y + off[1] + b, height: h, imageRendering: "pixelated",
      transform: `scale(${flip ? -sc : sc}, ${sc})`, transformOrigin: "50% 100%", filter: "drop-shadow(6px 6px 0 rgba(0,0,0,.55))" }} />
  );
};

// A pixel-block wipe: tiles cover the frame in a scattered order, then clear (the cut happens under them).
const PixelWipe: React.FC<{ at: number; color?: string; frames?: number }> = ({ at, color = C.ink, frames = 10 }) => {
  const f = useCurrentFrame() - at;
  if (f < 0 || f > frames) return null;
  const cols = 16, rows = 9, half = frames / 2;
  return (
    <AbsoluteFill>
      {Array.from({ length: cols * rows }, (_, i) => {
        const r = ((i * 97) % 89) / 89;
        const on = f < half ? f / half > r : (f - half) / half < r;
        return on ? <div key={i} style={{ position: "absolute", left: (i % cols) * 120, top: Math.floor(i / cols) * 120, width: 120, height: 120, background: i % 7 === 0 ? C.cyan : color }} /> : null;
      })}
    </AbsoluteFill>
  );
};

const Clip: React.FC<{ src: string; from?: number; volume?: number; style?: React.CSSProperties }> = ({ src, from = 0, volume = 0, style }) => {
  const layer = useLayer();
  const v = hears(layer, "voice") ? volume : 0;
  return <Video className="plate" src={staticFile(`footage/${src}`)} trimBefore={fr(from)} muted={v === 0} volume={v} style={{ width: "100%", height: "100%", objectFit: "cover", ...style }} />;
};

// An editor window drawn in pixels: title bar, a program monitor, four tracks that fill clip by clip.
const APPS = [
  { name: "Premiere Pro", bar: "#1F1A3D", accent: "#9999FF" },
  { name: "DaVinci Resolve", bar: "#202024", accent: C.orange },
  { name: "Final Cut Pro", bar: "#1B1B26", accent: C.purple },
];
const TRACKS = [
  { id: "V2", color: C.yellow, blocks: [[0.06, 0.16], [0.3, 0.42], [0.62, 0.7], [0.84, 0.95]] },
  { id: "V1", color: C.cyan, blocks: [[0, 0.22], [0.23, 0.4], [0.41, 0.58], [0.59, 0.81], [0.82, 1]] },
  { id: "A1", color: C.green, blocks: [[0, 0.4], [0.41, 0.81], [0.82, 1]] },
  { id: "A2", color: C.purple, blocks: [[0, 1]] },
];
const EditorWindow: React.FC<{ app: (typeof APPS)[number]; x: number; y: number; w: number; at: number; fill: number | null; thumb?: string }> = ({ app, x, y, w, at, fill, thumb }) => {
  const frame = useCurrentFrame();
  const f = frame - at;
  if (f < 0) return null;
  const sc = [0.3, 0.8, 1.08, 1][Math.min(3, Math.floor(f / 2))];
  const h = w * 0.66, tw = w - 70;
  let k = 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, transform: `scale(${sc})`, background: "#0E0D18", border: `5px solid ${C.ink}`, boxShadow: `10px 10px 0 ${C.ink}` }}>
      <div style={{ height: 44, background: app.bar, borderBottom: `4px solid ${app.accent}`, display: "flex", alignItems: "center", gap: 10, padding: "0 14px" }}>
        {[C.red, C.yellow, C.green].map((c) => <div key={c} style={{ width: 14, height: 14, background: c }} />)}
        <div style={{ fontFamily: "Jersey", fontSize: 34, color: C.white, marginLeft: 8 }}>{app.name}</div>
      </div>
      <div style={{ position: "absolute", left: 120, top: 60, width: w - 240, height: h * 0.36, background: "#000", border: `3px solid #333`, overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
        {thumb && fill !== null ? <Img src={staticFile(thumb)} style={{ width: "100%", height: "100%", objectFit: "cover", opacity: Math.min(1, (frame - fill) / 6) }} />
          : <div style={{ fontFamily: "Jersey", fontSize: 46, color: "#555", opacity: Math.floor(frame / 8) % 2 ? 1 : 0.4 }}>NO MEDIA</div>}
      </div>
      {TRACKS.map((t, ti) => (
        <div key={t.id} style={{ position: "absolute", left: 14, top: h * 0.36 + 80 + ti * 40, width: w - 28, height: 34, background: "#1A1928" }}>
          <div style={{ position: "absolute", left: 4, top: 0, fontFamily: "Jersey", fontSize: 30, color: "#888" }}>{t.id}</div>
          {t.blocks.map(([a, b]) => {
            const n = k++;
            if (fill === null) return null;
            const ff = frame - fill - n * 1.6;
            if (ff < 0) return null;
            const drop = [-90, -40, 6, 0][Math.min(3, Math.floor(ff / 1.5))];
            return <div key={a} style={{ position: "absolute", left: 50 + a * tw, top: drop, width: (b - a) * tw - 4, height: 34, background: t.color, borderBottom: `5px solid rgba(0,0,0,.35)` }} />;
          })}
        </div>
      ))}
    </div>
  );
};

const Windows: React.FC<{ at: number[]; fill: number | null; y?: number; scale?: number }> = ({ at, fill, y = 560, scale = 1 }) => (
  <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: "50% 60%" }}>
    {APPS.map((app, i) => <EditorWindow key={app.name} app={app} x={60 + i * 610} y={y + (i === 1 ? -24 : 0)} w={580} at={at[i]} fill={fill === null ? null : fill + i * 3} thumb="sprites/thumb.png" />)}
  </AbsoluteFill>
);

// 0. Hook: "Who says AI video can't be edited in" + Premiere, Resolve, Final Cut.
const Hook: React.FC = () => {
  const b = (n: number) => fr(n * BEAT);
  return (
    <AbsoluteFill>
      <Grid />
      <div style={{ position: "absolute", left: 80, top: 40 }}>
        <div style={{ display: "flex", gap: 34, alignItems: "baseline" }}>
          <Px size={200} at={0}>WHO</Px><Px size={200} at={b(1)}>SAYS</Px><Px size={200} at={b(2)} color={C.cyan}>AI VIDEO</Px>
        </div>
        <div style={{ display: "flex", gap: 34, alignItems: "baseline", marginTop: 10 }}>
          <Px size={150} at={b(3)} color={C.yellow}>CAN'T BE EDITED IN</Px>
        </div>
      </div>
      <Windows at={[b(4), b(5), b(6)]} fill={null} />
      <Sprite name="robot-ask" h={300} x={1600} y={170} at={b(7)} />
      <Px size={120} at={b(7)} color={C.orange} style={{ position: "absolute", left: 1560, top: 60 }}>?</Px>
    </AbsoluteFill>
  );
};

const Drop: React.FC = () => (
  <AbsoluteFill>
    <Grid />
    <Windows at={[-30, -30, -30]} fill={0} />
    <div style={{ position: "absolute", left: 90, top: 80 }}>
      <Px size={210} color={C.white}>WE DO.</Px>
      <Px size={84} at={fr(BEAT * 1.5)} color={C.cyan} style={{ marginTop: 18 }}>every cut. every layer. your original files.</Px>
    </div>
    <Sprite name="karlo-cheer" h={380} x={1600} y={60} at={fr(BEAT * 2)} />
  </AbsoluteFill>
);

const Title: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Grid tint="#1B1640" />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <Px size={300} color={C.white} depth={16}>ONESHOT-VIDEO</Px>
        <Px size={84} at={8} color={C.yellow} style={{ marginTop: 20 }}>one prompt. a real edit you can open.</Px>
      </AbsoluteFill>
      <Sprite name="robot-happy" h={380} x={130} y={620} at={4} enter="left" />
      <Sprite name="karlo-wave" h={420} x={1600} y={600} at={6} enter="right" />
      {f < 30 && <Img src={staticFile("sprites/sparkles.png")} style={{ position: "absolute", left: 1350, top: 160, height: 300, imageRendering: "pixelated", opacity: Math.floor(f / 3) % 2 }} />}
    </AbsoluteFill>
  );
};

// Raw phone recording, then the same sentence in the edit.
const RawToEdit: React.FC = () => {
  const f = useCurrentFrame();
  const wipe = fr(T.wipe - T.raw);
  const rec = Math.floor(f / 15) % 2;
  return (
    <AbsoluteFill>
      <Sequence durationInFrames={wipe + 5} layout="none"><AbsoluteFill><Clip src="raw_c.mp4" from={0.6} volume={1} /></AbsoluteFill></Sequence>
      <Sequence from={wipe + 5} layout="none"><AbsoluteFill><Clip src="edit_c.mp4" from={0.6 + (wipe + 5) / 30} volume={1} /></AbsoluteFill></Sequence>
      {f < wipe + 5 ? (
        <>
          <AbsoluteFill style={{ border: `14px solid ${C.ink}` }} />
          <div style={{ position: "absolute", left: 60, top: 48, display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{ width: 34, height: 34, background: C.red, opacity: rec }} />
            <Px size={84} stamp={false}>RAW · IMG_4861.MOV · 24:22</Px>
          </div>
          <Px size={64} at={10} color={C.yellow} style={{ position: "absolute", left: 60, top: 175 }}>shot on a phone from row 30</Px>
        </>
      ) : (
        <Px size={120} at={wipe + 5} color={C.yellow} style={{ position: "absolute", right: 70, top: 830 }}>THE EDIT ✦</Px>
      )}
      <PixelWipe at={wipe} />
      <Sfx at={T.wipe} src="powerup.wav" vol={0.35} />
    </AbsoluteFill>
  );
};

const AiTakes: React.FC = () => (
  <AbsoluteFill>
    <Clip src="edit_c.mp4" from={8.15} volume={1} />
  </AbsoluteFill>
);

// The stumbles the edit removed, as blocks the robot zaps.
const STUMBLES = [
  { text: "OKAY.", sound: "z_okay.wav", dur: 0.55 },
  { text: "SO, SH*T.", sound: "z_shit.wav", dur: 0.47 },
  { text: "COME ON, CLICK IT.", sound: "z_click.wav", dur: 0.47 },
  { text: "GOOD JOB.", sound: "z_goodjob.wav", dur: 0.47 },
  { text: "WELL, OBVIOUSLY,", sound: "z_obv.wav", dur: 0.47 },
  { text: "LET ME GET A SIP OF WATER", sound: "z_water.wav", dur: 0.9 },
];
const Zap: React.FC = () => {
  const f = useCurrentFrame();
  const z = ZAPS.map((t) => fr(t - T.zap));
  const done = z.filter((t) => f >= t + 3).length;
  const secs = Math.round(interpolate(f, [z[0], z[5] + 6], [24 * 60 + 22, 14 * 60 + 51], clamp));
  const clock = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
  const target = Math.max(0, z.findIndex((t) => f < t + 3));
  const rx = 90 + (target % 3) * 600 + 280;
  return (
    <AbsoluteFill>
      <Grid tint="#120F26" />
      <Px size={110} color={C.yellow} style={{ position: "absolute", left: 70, top: 50 }}>CUT THE STUMBLES</Px>
      <div style={{ position: "absolute", right: 70, top: 40, textAlign: "right" }}>
        <Px size={64} color="#999" stamp={false}>TIME</Px>
        <Px size={150} color={done === 6 ? C.green : C.white} stamp={false}>{clock}</Px>
      </div>
      {STUMBLES.map((s, i) => {
        const x = 90 + (i % 3) * 600, y = 330 + Math.floor(i / 3) * 230;
        const hit = f - z[i];
        if (hit >= 6) return <Px key={s.text} size={70} color={C.green} stamp={false} style={{ position: "absolute", left: x + 140, top: y + 40, opacity: hit < 14 ? 1 : 0 }}>+{i === 5 ? 2 : 1}s</Px>;
        const shake = hit >= 0 ? (hit % 2 ? 8 : -8) : 0;
        return (
          <div key={s.text} style={{ position: "absolute", left: x + shake, top: y, width: 560, height: 180, background: hit >= 0 ? C.white : C.red, border: `6px solid ${C.ink}`, boxShadow: `8px 8px 0 ${C.ink}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ fontFamily: "Jersey", fontSize: s.text.length > 18 ? 52 : 76, color: C.white, textShadow: shadow(4) }}>{s.text}</div>
            {hit >= 0 && hit < 6 && <Img src={staticFile("sprites/burst.png")} style={{ position: "absolute", left: 150, top: -80, height: 300, imageRendering: "pixelated" }} />}
          </div>
        );
      })}
      {z.map((t, i) => f >= t - 2 && f < t + 1 ? <div key={i} style={{ position: "absolute", left: 90 + (i % 3) * 600 + 273, top: 330 + Math.floor(i / 3) * 230 + 180, width: 14, height: 860 - (330 + Math.floor(i / 3) * 230 + 180), background: C.cyan, boxShadow: `0 0 30px ${C.cyan}` }} /> : null)}
      <Sprite name="robot" h={300} x={rx - 130} y={790} bob={false} enter="up" />
    </AbsoluteFill>
  );
};

// Long form: dive from the raw room into the stage, then the edit, two beats a shot.
const Dive: React.FC = () => {
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = interpolate(f, [0, durationInFrames], [0, 1], { ...clamp, easing: (t) => t * t * t });
  const s = 1 + 0.75 * p;
  const tx = 260 * s * p, ty = -57 * s * p;
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <AbsoluteFill style={{ transform: `translate(${tx}px, ${ty}px) scale(${s})` }}><Clip src="raw_dive.mp4" /></AbsoluteFill>
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(11,9,24,.85) 0%, rgba(11,9,24,.4) 30%, rgba(11,9,24,0) 45%)" }} />
      <div style={{ position: "absolute", left: 70, top: 60 }}>
        <Px size={240} color={C.white} depth={12}>LONG FORM</Px>
        <Px size={84} at={10} color={C.yellow} style={{ marginTop: 10 }}>24 min of phone footage → a 15-min film</Px>
      </div>
    </AbsoluteFill>
  );
};
const LONG_SHOTS = [
  { src: "e_stage.mp4", from: 0.1, tag: "best angle on every sentence" },
  { src: "e_cave.mp4", from: 0.1, tag: "graphics on the beat" },
  { src: "e_next.mp4", from: 0.3, tag: "the slides, rebuilt" },
  { src: "e_earth.mp4", from: 0.1, tag: "9 chapters · subtitles" },
];
const LongShot: React.FC<{ i: number }> = ({ i }) => {
  const s = LONG_SHOTS[i];
  return (
    <AbsoluteFill>
      <Clip src={s.src} from={s.from} />
      <div style={{ position: "absolute", left: 60, bottom: 150, background: C.ink, padding: "8px 26px 14px", boxShadow: `8px 8px 0 ${C.cyan}` }}>
        <Px size={76} color={C.white}>{s.tag}</Px>
      </div>
      <div style={{ position: "absolute", right: 60, top: 50 }}><Px size={90} color={C.yellow} stamp={false}>14:51</Px></div>
    </AbsoluteFill>
  );
};

// Short form: the long form folds into a phone; three clips, one at a time, full height, with their sound.
const SHORTS = [
  { src: "short1.mp4", tag: "WORDS BEHIND YOU" },
  { src: "short2.mp4", tag: "TAKEOVERS" },
  { src: "short3.mp4", tag: "IT FOLLOWS THE SPEAKER" },
];
const Phone: React.FC<{ src: string; volume?: number }> = ({ src, volume = 1 }) => (
  <div style={{ position: "absolute", left: 960 - 290, top: 40, width: 580, height: 1000, border: `14px solid ${C.ink}`, borderRadius: 48, overflow: "hidden", boxShadow: `16px 16px 0 ${C.ink}`, background: "#000" }}>
    <Clip src={src} volume={volume} />
  </div>
);
const ShortIntro: React.FC = () => {
  const f = useCurrentFrame();
  const p = Math.min(1, twos(f) / 12);
  const w = 1920 - (1920 - 580) * p, h = 1080 - (1080 - 1000) * p;
  return (
    <AbsoluteFill>
      <Grid tint="#1B1640" />
      <Px size={300} color={C.orange} depth={16} style={{ position: "absolute", left: 0, right: 0, top: 360, textAlign: "center" }}>SHORT FORM</Px>
      <div style={{ position: "absolute", left: 960 - w / 2, top: 40 + (1000 - h) / 2 - (1 - p) * 40, width: w, height: h, border: `${14 * p}px solid ${C.ink}`, borderRadius: 48 * p, overflow: "hidden", opacity: 1 - p * 0.0 }}>
        <Clip src="e_earth.mp4" from={0.9} style={{ opacity: 1 - p }} />
      </div>
    </AbsoluteFill>
  );
};
const ShortSlot: React.FC<{ i: number }> = ({ i }) => {
  const s = SHORTS[i];
  const side = i % 2 ? "right" : "left";
  return (
    <AbsoluteFill>
      <Grid tint={["#1B1640", "#2A1030", "#0F2236"][i]} />
      <Px size={380} color="rgba(255,255,255,0.10)" depth={0} stamp={false} style={{ position: "absolute", left: 0, right: 0, top: 300, textAlign: "center" }}>{["SHORTS", "REELS", "TIKTOK"][i]}</Px>
      <Phone src={s.src} />
      <div style={{ position: "absolute", [side]: 70, top: 420, width: 520, textAlign: side }}>
        <Px size={96} color={C.yellow} at={3} style={{ whiteSpace: "normal" }}>{s.tag}</Px>
      </div>
      <Sprite name={["karlo-point", "robot-star", "karlo-look"][i]} h={380} x={side === "left" ? 1480 : 160} y={640} at={4} flip={side === "right"} />
    </AbsoluteFill>
  );
};

const Scratch: React.FC = () => {
  const r = fr(T.reveal - T.scratch);
  const b = r + fr(1.875);
  return (
    <AbsoluteFill>
      <Sequence durationInFrames={r} layout="none">
        <AbsoluteFill><Grid />
          <Px size={210} color={C.white} style={{ position: "absolute", left: 90, top: 130 }}>NO FOOTAGE</Px>
          <Px size={210} color={C.orange} at={4} style={{ position: "absolute", left: 90, top: 330 }}>AT ALL?</Px>
          <Sprite name="robot-ask" h={460} x={1150} y={520} />
          <Sprite name="gift-blue" h={300} x={1520} y={680} at={6} />
        </AbsoluteFill>
      </Sequence>
      <Sequence from={r} durationInFrames={b - r} layout="none"><AbsoluteFill><Clip src="reveal_a.mp4" from={2.4} volume={1} /></AbsoluteFill></Sequence>
      <Sequence from={b} layout="none"><AbsoluteFill><Clip src="reveal_b.mp4" from={0.6} volume={1} /></AbsoluteFill></Sequence>
      <Sequence from={r} layout="none">
        <div style={{ position: "absolute", left: 60, bottom: 60, background: C.ink, padding: "8px 26px 14px", boxShadow: `8px 8px 0 ${C.orange}` }}>
          <Px size={70} color={C.white}>FROM SCRATCH · a 6-second clip, a song and a logo</Px>
        </div>
      </Sequence>
    </AbsoluteFill>
  );
};

const Idea: React.FC = () => (
  <AbsoluteFill>
    <Clip src="edit_idea.mp4" from={1.2} volume={1} />
  </AbsoluteFill>
);

const Logo: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Grid tint="#1B1640" />
      <Windows at={[-30, -30, -30]} fill={-60} y={660} scale={0.8} />
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 70 }}>
        <Px size={260} color={C.white} depth={16}>ONESHOT-VIDEO</Px>
        <Px size={80} at={6} color={C.yellow} style={{ marginTop: 14 }}>editable in Premiere · Resolve · Final Cut</Px>
        <div style={{ marginTop: 22, background: C.ink, padding: "6px 26px 12px", boxShadow: `8px 8px 0 ${C.cyan}`, opacity: f >= 10 ? 1 : 0 }}>
          <Px size={66} color={C.green} stamp={false}>{"> claude plugin install oneshot-video"}</Px>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Music: ducks under every voice and clip; silent under the Boston opener, which plays its own song.
const musicVolume = (frame: number) => {
  const t = frame / 30;
  if (t >= T.scratch + 0.9 && t < T.idea) return 0;
  if (t >= T.raw && t < T.zap) return 0.22;
  if (t >= T.zap && t < T.long) return 0.5;
  if (t >= T.shorts && t < T.scratch) return 0.25;
  if (t >= T.idea && t < T.logo) return 0.3;
  return 0.9;
};

export const Main: React.FC<{ layer?: Layer }> = ({ layer = "full" }) => (
  <Film layer={layer}>
    <Seg a={T.hook} b={T.drop} name="Hook"><Hook /></Seg>
    <Seg a={T.drop} b={T.title} name="Timelines"><Drop /></Seg>
    <Seg a={T.title} b={T.raw} name="Title"><Title /></Seg>
    <Seg a={T.raw} b={T.ai} name="Raw to edit"><RawToEdit /></Seg>
    <Seg a={T.ai} b={T.zap} name="AI takes it"><AiTakes /></Seg>
    <Seg a={T.zap} b={T.long} name="Stumbles"><Zap /></Seg>
    <Seg a={T.long} b={T.longCuts} name="Dive"><Dive /></Seg>
    {LONG_SHOTS.map((_, i) => <Seg key={i} a={T.longCuts + i * 2 * BEAT} b={T.longCuts + (i + 1) * 2 * BEAT} name={`Long ${i + 1}`}><LongShot i={i} /></Seg>)}
    <Seg a={T.short} b={T.shorts} name="Fold"><ShortIntro /></Seg>
    {SHORT_SLOTS.map((t, i) => <Seg key={i} a={t} b={SHORT_SLOTS[i + 1] ?? T.scratch} name={`Short ${i + 1}`}><ShortSlot i={i} /></Seg>)}
    <Seg a={T.scratch} b={T.idea} name="From scratch"><Scratch /></Seg>
    <Seg a={T.idea} b={T.logo} name="The idea"><Idea /></Seg>
    <Seg a={T.logo} b={T.total} name="Logo"><Logo /></Seg>

    {[T.windows, T.windows + BEAT, T.windows + 2 * BEAT].map((t, i) => <Sfx key={`w${i}`} at={t} src="blip2.wav" vol={0.4} />)}
    {[0, 1, 2, 3].map((i) => <Sfx key={`h${i}`} at={i * BEAT} src="blip.wav" vol={0.35} />)}
    <Sfx at={T.windows + 3 * BEAT} src="buzz.wav" vol={0.3} />
    <Sfx at={T.drop} src="stamp.wav" vol={0.7} />
    <Sfx at={T.title} src="coin.wav" vol={0.5} />
    {ZAPS.map((t, i) => <React.Fragment key={`z${i}`}><Sfx at={t - 0.06} src="zap.wav" vol={0.35} /><Sfx at={t} src={`audio/${STUMBLES[i].sound}`} vol={0.95} dur={STUMBLES[i].dur} /></React.Fragment>)}
    <Sfx at={ZAPS[5] + 0.25} src="powerup.wav" vol={0.4} />
    <Sfx at={T.long} src="jump.wav" vol={0.4} />
    {LONG_SHOTS.map((_, i) => <Sfx key={`l${i}`} at={T.longCuts + i * 2 * BEAT} src="blip2.wav" vol={0.3} />)}
    <Sfx at={T.short} src="stamp.wav" vol={0.6} />
    {SHORT_SLOTS.map((t, i) => <Sfx key={`s${i}`} at={t} src="coin.wav" vol={0.3} />)}
    <Sfx at={T.scratch} src="blip2.wav" vol={0.4} />
    <Sfx at={T.logo} src="coin.wav" vol={0.5} />
    {hears(layer, "music") && <Audio src={staticFile("audio/chip128.wav")} volume={musicVolume} />}
  </Film>
);
