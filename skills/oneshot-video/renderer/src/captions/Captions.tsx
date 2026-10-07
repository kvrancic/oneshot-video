import React, { useMemo } from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { EASE, Format, Palette, SAFE, SHADOW, SPRING, DIMS, isVertical } from "../theme";
import { layoutPages, Page, Token } from "./layout";
import { presetFor } from "./presets";

export type CaptionZone = { from: number; to: number; y?: number; dim?: number; hide?: boolean };

type Props = {
  tokens: Token[];
  preset: string;
  format: Format;
  palette: Palette;
  sentenceStarts: number[]; // token indices that open a sentence
  zones?: CaptionZone[]; // per-time overrides: move (split layouts), dim (overlay needs attention), hide
  split?: boolean; // captions sit in the seam of a stacked layout
  region?: { x0: number; x1: number }; // centre captions inside this horizontal band (side layouts)
};

const SOFT = "0 2px 12px rgba(0,0,0,.45)";

export const Captions: React.FC<Props> = ({ tokens, preset, format, palette, sentenceStarts, zones = [], split, region }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const p = presetFor(preset);
  const vertical = isVertical(format);
  const { w: W } = DIMS[format];
  const safe = SAFE[format];
  const maxWidth = region ? region.x1 - region.x0 : safe.x1 - safe.x0 - (vertical ? 0 : 300);

  const pages = useMemo(
    () => layoutPages(tokens, p, vertical, maxWidth, new Set(sentenceStarts)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tokens, preset, vertical, maxWidth, sentenceStarts],
  );

  const idx = pages.findIndex((pg) => t >= pg.showFrom && t < pg.showTo);
  if (idx < 0) return null;
  const page = pages[idx];
  const zone = zones.find((z) => t >= z.from && t < z.to);
  if (zone?.hide) return null;

  const size = vertical ? p.size.v : p.size.h;
  const baseY = zone?.y ?? (vertical ? (split ? p.y.vSplit ?? p.y.v : p.y.v) : p.y.h);
  const baselineOffset = (page.lineHeightPx - 1.21 * size) / 2 + 0.97 * size;
  const top = baseY - (page.lineWidths.length - 1) * page.lineHeightPx - baselineOffset;

  // Horizontal placement.
  const side = p.align === "speaker" ? (page.speaker === "B" ? "right" : "left") : p.align;
  const blockLeft = region
    ? Math.round((region.x0 + region.x1 - page.width) / 2)
    : side === "left" ? safe.x0 : side === "right" ? safe.x1 - page.width : Math.round((W - page.width) / 2);
  const lineOffset = (line: number) => {
    const lw = page.lineWidths[line];
    if (side === "left") return 0;
    if (side === "right") return page.width - lw;
    return (page.width - lw) / 2;
  };

  // Page-level entrance / exit.
  const fIn = frame - Math.round(page.showFrom * fps);
  const fOut = Math.round(page.showTo * fps) - frame;
  const next = pages[idx + 1];
  const hardCut = next && next.showFrom - page.showTo < 3 / fps;
  const exitOpacity = hardCut ? 1 : interpolate(fOut, [0, p.exitFrames], [0, 1], { extrapolateRight: "clamp", easing: EASE.exit });

  let pageOpacity = exitOpacity;
  let pageTransform = "";
  if (p.anim === "chunk-pop") {
    const s = spring({ frame: fIn, fps, config: SPRING.snap });
    pageOpacity *= interpolate(fIn, [0, 3], [0, 1], { extrapolateRight: "clamp" });
    pageTransform = `translateY(${(1 - s) * 10}px) scale(${0.92 + 0.08 * s})`;
  } else if (p.anim === "karaoke" || p.anim === "box") {
    const k = interpolate(fIn, [0, 7], [0, 1], { extrapolateRight: "clamp", easing: EASE.enter });
    pageOpacity *= k;
    pageTransform = `translateY(${(1 - k) * 8}px)`;
  } else if (p.anim === "slide-side") {
    const k = interpolate(fIn, [0, 9], [0, 1], { extrapolateRight: "clamp", easing: EASE.enter });
    const dir = side === "right" ? 1 : -1;
    pageOpacity *= k;
    pageTransform = `translateX(${dir * (1 - k) * 24}px)`;
  }
  pageOpacity *= zone?.dim ?? 1;

  const shadow = p.shadow === "display" ? SHADOW.display : p.shadow === "body" ? SHADOW.body : SOFT;
  const baseColor = page.speaker === "B" ? palette.cool : palette.text;

  // Karaoke box: one rect that glides between word rects.
  let box: React.ReactNode = null;
  if (p.anim === "box") {
    const found = page.words.findIndex((w, i) => t >= w.start - 0.033 && (i === page.words.length - 1 || t < page.words[i + 1].start - 0.033));
    const active = found < 0 ? 0 : found;
    {
      const w = page.words[active];
      const prev = page.words[Math.max(0, active - 1)];
      const since = frame - Math.round((w.start - 0.033) * fps);
      const s = active === 0 ? 1 : spring({ frame: since, fps, config: SPRING.box });
      const rect = (lw: typeof w) => ({
        x: blockLeft + lineOffset(lw.line) + lw.x,
        y: top + lw.line * page.lineHeightPx,
        w: lw.width,
      });
      const a = rect(prev);
      const b = rect(w);
      const padX = size * 0.16;
      const x = a.x + (b.x - a.x) * s;
      const y = a.y + (b.y - a.y) * s;
      const bw = a.w + (b.w - a.w) * s;
      box = (
        <div
          style={{
            position: "absolute",
            left: x - padX,
            top: y + page.lineHeightPx * 0.08,
            width: bw + padX * 2,
            height: page.lineHeightPx * 0.9,
            borderRadius: size * 0.2,
            background: p.boxColor === "text" ? palette.text : palette.accent,
          }}
        />
      );
    }
  }

  const scrim = p.scrim ? (
    <div
      style={{
        position: "absolute",
        left: blockLeft - p.scrim.padX,
        top: top - p.scrim.padY,
        width: page.width + p.scrim.padX * 2,
        height: page.height + p.scrim.padY * 2,
        background: p.scrim.bg,
        borderRadius: p.scrim.radius,
      }}
    />
  ) : null;

  return (
    <AbsoluteFill style={{ opacity: pageOpacity, transform: pageTransform, transformOrigin: `50% ${baseY}px` }}>
      {scrim}
      {box}
      {page.words.map((w, i) => {
        const wf = frame - Math.round((w.start - 0.033) * fps);
        const spoken = t >= w.start - 0.033;
        let opacity = 1;
        let ty = 0;
        let scale = 1;
        let color = w.emph === "accent" ? palette.accent : baseColor;
        if (p.anim === "karaoke") {
          opacity = spoken ? interpolate(wf, [0, 3], [p.unspokenOpacity, 1], { extrapolateRight: "clamp" }) : p.unspokenOpacity;
          if (w.emph === "accent" && !spoken) color = baseColor;
        } else if (p.anim === "word-rise") {
          const k = interpolate(frame - Math.round((w.start - p.leadMs / 1000) * fps), [0, 12], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: EASE.confident,
          });
          opacity = k;
          ty = (1 - k) * 12;
        } else if (p.anim === "word-etch") {
          const dur = p.name === "DUSK" ? 18 : 15;
          opacity = interpolate(frame - Math.round((w.start - p.leadMs / 1000) * fps), [0, dur], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: EASE.calm,
          });
        } else if (p.anim === "box") {
          const active = (t >= w.start - 0.033 || i === 0) && (i === page.words.length - 1 || t < page.words[i + 1].start - 0.033);
          opacity = active ? 1 : spoken ? 1 : p.unspokenOpacity;
          if (active) color = p.boxColor === "text" ? palette.ink : palette.ink;
        } else if (p.anim === "chunk-pop" && w.emph === "accent") {
          color = spoken ? palette.accent : baseColor;
          scale = spoken ? interpolate(wf, [0, 3, 6], [1, p.emphasisScale, 1], { extrapolateRight: "clamp" }) : 1;
        }
        const serif = w.family !== "Inter";
        return (
          <span
            key={i}
            style={{
              position: "absolute",
              left: blockLeft + lineOffset(w.line) + w.x,
              top: top + w.line * page.lineHeightPx + (serif ? page.lineHeightPx * 0.02 : 0),
              width: w.width + 2,
              lineHeight: `${page.lineHeightPx}px`,
              fontFamily: w.family,
              fontSize: w.fontSize,
              fontWeight: w.weight,
              fontStyle: w.italic ? "italic" : "normal",
              letterSpacing: serif ? "0em" : `${p.tracking}em`,
              fontFeatureSettings: '"ss01" 0, "cv11" 1, "tnum" 0',
              color: serif && p.name !== "EPIGRAPH" ? "#FFFFFF" : color,
              opacity,
              transform: `translateY(${ty}px) scale(${scale})`,
              transformOrigin: "50% 85%",
              textShadow: p.anim === "box" && color === palette.ink ? "none" : shadow,
              whiteSpace: "pre",
            }}
          >
            {w.text}
          </span>
        );
      })}
    </AbsoluteFill>
  );
};

export type { Page, Token };
