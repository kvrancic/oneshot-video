import React from "react";
import { AbsoluteFill, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { Captions, CaptionZone } from "./captions/Captions";
import type { Token } from "./captions/layout";
import { StanceBoard } from "./graphics/StanceBoard";
import { SwapQuote } from "./graphics/SwapQuote";
import { BigNumber, NextToken, Steps, Timeline, Tokens } from "./graphics/Explainers";
import { BlackBox } from "./graphics/BlackBox";
import { ChapterCard, EndCard, Footnote, HookBar, KeywordChip, NameTag, NumberCallout, ProgressBar, QuoteCard, Takeover } from "./overlays/Cards";
import { Grain } from "./overlays/Grain";
import { TextBehind } from "./overlays/TextBehind";
import { DIMS, EASE, Format, PALETTES, PaletteName, RADIUS, SHADOW, isVertical } from "./theme";
import { useFontsReady } from "./useFonts";

type Visual =
  | { kind: "graphic"; graphic: "StanceBoard" | "SwapQuote" | "BigNumber" | "Timeline" | "Tokens" | "NextToken" | "Steps" | "BlackBox"; props: Record<string, unknown>; panelH?: number }
  | { kind: "image" | "slide"; src: string; fit?: "cover" | "contain"; kenburns?: { from: [number, number, number]; to: [number, number, number] }; highlight?: { x: number; y: number; w: number; h: number; at: number }; panelH?: number }
  | { kind: "video"; src: string; trimBefore?: number; fit?: "cover" | "contain"; panelH?: number };

type Span = { from: number; to: number; mode: "stage" | "visual" | "speaker"; visual?: Visual; cut?: boolean }; // cut: enter without the fade
type Overlay = { type: string; from: number; to: number; props?: Record<string, unknown> };

export type ClipProps = {
  id: string;
  format: Format;
  fps: number;
  durationInFrames: number;
  palette: PaletteName;
  plate: string;
  stagePlate?: string | null; // 16:9 stage layouts: speaker-only shot for the right third (820x1080)
  face: { every: number; xy: [number, number][] };
  captions: { preset: string; tokens: Token[]; sentenceStarts: number[]; zones: CaptionZone[]; off?: boolean };
  layout: Span[];
  overlays: Overlay[];
  hook?: { text: string; to: number; collapseAt?: number; persist?: boolean; treatment?: "paper" | "float" } | null;
  end?: { text: string; handle?: string; from: number } | null;
  progress?: boolean;
  grain?: number;
};

const STAGE_TOP = 150;
const IN_F = 14;
const OUT_F = 12;

const faceAt = (face: ClipProps["face"], frame: number): [number, number] => {
  const i = frame / face.every;
  const a = Math.max(0, Math.min(face.xy.length - 1, Math.floor(i)));
  const b = Math.min(face.xy.length - 1, a + 1);
  const k = i - a;
  return [face.xy[a][0] * (1 - k) + face.xy[b][0] * k, face.xy[a][1] * (1 - k) + face.xy[b][1] * k];
};

const panelHeight = (v: Visual | undefined, vertical: boolean) => {
  if (!v) return 0;
  if (v.panelH) return v.panelH;
  if (!vertical) return 0;
  return v.kind === "graphic" ? 820 : 608;
};

const VisualView: React.FC<{ v: Visual; w: number; h: number; palette: PaletteName; format: Format; t0: number; dur: number }> = ({ v, w, h, palette, format, t0, dur }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pal = PALETTES[palette];
  if (v.kind === "graphic") {
    if (v.graphic === "StanceBoard") {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return <StanceBoard {...(v.props as any)} w={w} h={h} palette={pal} t0={t0} vertical={isVertical(format)} />;
    }
    const gx = { w, h, palette: pal, t0, vertical: isVertical(format) };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gp = v.props as any;
    if (v.graphic === "BigNumber") return <BigNumber {...gp} {...gx} />;
    if (v.graphic === "Timeline") return <Timeline {...gp} {...gx} />;
    if (v.graphic === "Tokens") return <Tokens {...gp} {...gx} />;
    if (v.graphic === "NextToken") return <NextToken {...gp} {...gx} />;
    if (v.graphic === "Steps") return <Steps {...gp} {...gx} />;
    if (v.graphic === "BlackBox") return <BlackBox {...gp} {...gx} />;
    if (v.graphic === "SwapQuote") {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return <SwapQuote {...(v.props as any)} w={w} h={h} palette={pal} t0={t0} vertical={isVertical(format)} />;
    }
    return null;
  }
  if (v.kind === "video") {
    return (
      <Video src={staticFile(v.src)} muted trimBefore={v.trimBefore ? Math.round(v.trimBefore * fps) : undefined}
        style={{ width: w, height: h, objectFit: v.fit ?? "cover" }} />
    );
  }
  const kb = v.kenburns ?? (v.kind === "slide" ? { from: [1, 50, 50], to: [1.04, 50, 50] } : { from: [1.02, 50, 50], to: [1.1, 50, 45] });
  const k = interpolate(frame, [0, dur], [0, 1], { extrapolateRight: "clamp", easing: EASE.calm });
  const s = kb.from[0] + (kb.to[0] - kb.from[0]) * k;
  const ox = kb.from[1] + (kb.to[1] - kb.from[1]) * k;
  const oy = kb.from[2] + (kb.to[2] - kb.from[2]) * k;
  const hl = v.kind === "slide" && v.highlight ? v.highlight : null;
  const hk = hl ? interpolate(frame, [Math.round((hl.at - t0) * fps), Math.round((hl.at - t0) * fps) + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move }) : 0;
  return (
    <div style={{ width: w, height: h, overflow: "hidden", position: "relative", background: v.kind === "slide" ? "#fff" : pal.ground }}>
      <div style={{ position: "absolute", inset: 0, transform: `scale(${s})`, transformOrigin: `${ox}% ${oy}%` }}>
        <Img src={staticFile(v.src)} style={{ width: "100%", height: "100%", objectFit: v.fit ?? (v.kind === "slide" ? "contain" : "cover") }} />
        {hl ? (
          <div style={{ position: "absolute", left: `${hl.x * 100}%`, top: `${hl.y * 100}%`, width: `${hl.w * 100}%`, height: `${hl.h * 100}%`,
            background: pal.accent, opacity: 0.38, mixBlendMode: "multiply", transform: `scaleX(${hk}) skewX(-1deg)`, transformOrigin: "left", borderRadius: 3 }} />
        ) : null}
      </div>
    </div>
  );
};

const OverlayView: React.FC<{ o: Overlay; format: Format; palette: PaletteName; dur: number; faceY?: number; sideX?: number }> = ({ o, format, palette, dur, faceY, sideX }) => {
  // In a 16:9 stage layout (sideX set) a takeover stays over the panel, clear of the speaker.
  const pal = PALETTES[palette];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const p = (o.props ?? {}) as any;
  const base = { format, palette: pal, dur, t0: o.from };
  switch (o.type) {
    case "NameTag": return <NameTag {...base} x={sideX} {...p} />;
    case "KeywordChip": return <KeywordChip {...base} {...p} />;
    case "QuoteCard": return <QuoteCard {...base} {...p} />;
    case "Takeover": return <Takeover {...base} maxRight={sideX !== undefined ? sideX - 80 : undefined} {...p} />;
    case "Footnote": return <Footnote {...base} {...p} />;
    case "ChapterCard": return <ChapterCard {...base} {...p} />;
    case "HookBar": return <HookBar {...base} {...p} />;
    case "NumberCallout": return <NumberCallout {...base} {...p} />;
    case "TextBehind": return <TextBehind {...base} faceY={faceY} {...p} />;
    default: return null;
  }
};

export const Clip: React.FC<ClipProps> = (props) => {
  const ready = useFontsReady();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { format } = props;
  const { w: W, h: H } = DIMS[format];
  const vertical = isVertical(format);
  const pal = PALETTES[props.palette];
  const t = frame / fps;

  // Which layout span is active, and how far into its entrance/exit we are.
  const span = props.layout.find((s) => t >= s.from && t < s.to);
  const prev = props.layout.filter((s) => s.to <= t + 1e-6).slice(-1)[0];
  let stageK = 0;
  let activeStage: Span | undefined;
  if (span && span.mode !== "speaker") {
    activeStage = span;
    const fIn = frame - Math.round(span.from * fps);
    const fOut = Math.round(span.to * fps) - frame;
    const nextSpan = props.layout.find((s) => Math.abs(s.from - span.to) < 0.05);
    const contIn = span.cut || (prev && Math.abs(prev.to - span.from) < 0.05 && prev.mode === span.mode);
    const contOut = nextSpan && nextSpan.mode === span.mode;
    stageK = Math.min(
      contIn ? 1 : interpolate(fIn, [0, IN_F], [0, 1], { extrapolateRight: "clamp", easing: EASE.move }),
      contOut ? 1 : interpolate(fOut, [0, OUT_F], [0, 1], { extrapolateRight: "clamp", easing: EASE.move }),
    );
  }
  const mode = activeStage?.mode ?? "speaker";
  const panelH = panelHeight(activeStage?.visual, vertical);

  // Plate placement.
  const [fx, fy] = faceAt(props.face, frame);
  let plateStyle: React.CSSProperties = { position: "absolute", left: 0, top: 0, width: W, height: H };
  let plateClip = "none";
  if (mode === "stage" && vertical) {
    const areaTop = STAGE_TOP + panelH + 20;
    const target = areaTop + 0.2 * (H - areaTop); // eyes high in the speaker area, captions below the chin
    const ty = Math.max(0, Math.min(areaTop, target - fy)) * stageK;
    plateStyle = { ...plateStyle, transform: `translateY(${ty}px)` };
    plateClip = `inset(${Math.max(0, (areaTop - ty) * stageK)}px 0 0 0)`;
  } else if (mode === "stage" && !vertical && !props.stagePlate) {
    const shift = Math.max(0, Math.min(460, 1380 - fx)) * stageK;
    plateStyle = { ...plateStyle, transform: `translateX(${shift}px)` };
    plateClip = `inset(0 0 0 ${(1080 - shift) * stageK}px)`;
  }
  const sideShot = mode === "stage" && !vertical && !!props.stagePlate;
  const plateHidden = (mode === "visual" || sideShot) && stageK >= 1;

  const stageBox = vertical
    ? { left: 0, top: STAGE_TOP, width: W, height: panelH }
    : { left: 72, top: 90, width: 1000, height: 900 };

  const captionsSplit = mode === "stage" && vertical && stageK > 0.5;
  const endFrom = props.end ? Math.round(props.end.from * fps) : Infinity;

  return (
    <AbsoluteFill style={{ backgroundColor: pal.ground }}>
      {!plateHidden ? (
        <AbsoluteFill style={{ clipPath: plateClip }}>
          <div style={plateStyle}>
            <Video src={staticFile(props.plate)} muted style={{ width: W, height: H }} />
          </div>
        </AbsoluteFill>
      ) : null}

      {props.stagePlate && !vertical ? (
        <AbsoluteFill style={{ opacity: sideShot ? stageK : 0 }}>
          <div style={{ position: "absolute", left: W - 820, top: 0, width: 820, height: H }}>
            <Video src={staticFile(props.stagePlate)} muted style={{ width: 820, height: H }} />
          </div>
        </AbsoluteFill>
      ) : null}

      {props.layout.map((s, i) => {
        if (s.mode === "speaker" || !s.visual) return null;
        const from = Math.round(s.from * fps);
        const dur = Math.max(1, Math.round((s.to - s.from) * fps));
        const isVisual = s.mode === "visual";
        const ph = panelHeight(s.visual, vertical);
        const box = isVisual ? { left: 0, top: 0, width: W, height: H } : vertical ? { ...stageBox, height: ph } : stageBox;
        return (
          <Sequence key={i} from={from} durationInFrames={dur} layout="none">
            <StagePanel box={box} k={activeStage === s ? stageK : 1} vertical={vertical} visual={isVisual} ground={pal.ground}>
              <VisualView v={s.visual} w={box.width} h={box.height} palette={props.palette} format={format} t0={s.from} dur={dur} />
            </StagePanel>
          </Sequence>
        );
      })}

      {props.overlays.filter((o) => o.type !== "EndCard").map((o, i) => {
        const from = Math.round(o.from * fps);
        const dur = Math.max(1, Math.round((o.to - o.from) * fps));
        return (
          <Sequence key={`o${i}`} from={from} durationInFrames={dur} layout="none">
            {ready ? <OverlayView o={o} format={format} palette={props.palette} dur={dur} faceY={faceAt(props.face, from + Math.round(dur / 3))[1]}
              sideX={!vertical && props.stagePlate && props.layout.some((s) => s.mode === "stage" && o.from >= s.from && o.from < s.to) ? W - 820 + 48 : undefined} /> : null}
          </Sequence>
        );
      })}

      {props.hook && ready ? (
        <Sequence from={0} durationInFrames={Math.max(1, Math.round(props.hook.to * fps))} layout="none">
          <HookBar format={format} palette={pal} dur={Math.round(props.hook.to * fps)} text={props.hook.text}
            collapseAt={props.hook.collapseAt} persist={props.hook.persist} treatment={props.hook.treatment} instant />
        </Sequence>
      ) : null}

      {ready && !props.captions.off && frame < endFrom ? (
        <Captions tokens={props.captions.tokens} preset={props.captions.preset} format={format} palette={pal}
          sentenceStarts={props.captions.sentenceStarts} zones={props.captions.zones} split={captionsSplit}
          region={sideShot && stageK > 0.5 ? { x0: W - 820 + 40, x1: W - 40 } : undefined} />
      ) : null}

      {props.progress ? <ProgressBar format={format} palette={pal} progress={frame / props.durationInFrames} /> : null}

      {props.end && ready ? (
        <Sequence from={endFrom} layout="none">
          <EndCard format={format} palette={pal} dur={props.durationInFrames - endFrom} text={props.end.text} handle={props.end.handle} />
        </Sequence>
      ) : null}

      {props.grain ? <Grain amount={props.grain} /> : null}
    </AbsoluteFill>
  );
};

const StagePanel: React.FC<{ box: { left: number; top: number; width: number; height: number }; k: number; vertical: boolean; visual: boolean; ground: string; children: React.ReactNode }> = ({
  box, k, vertical, visual, ground, children,
}) => {
  const style: React.CSSProperties = visual
    ? { position: "absolute", ...box, opacity: k, background: ground }
    : vertical
      ? { position: "absolute", ...box, background: ground, clipPath: `inset(0 0 ${(1 - k) * 100}% 0)`, transform: `translateY(${(1 - k) * -24}px)` }
      : { position: "absolute", ...box, borderRadius: RADIUS, overflow: "hidden", boxShadow: SHADOW.card, background: ground,
          opacity: k, transform: `translateX(${(1 - k) * -40}px)` };
  return <div style={style}>{children}</div>;
};
