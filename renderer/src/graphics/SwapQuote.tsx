import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { EASE, FONT, Palette, RADIUS, SHADOW, SPRING } from "../theme";

// A quote on a paper card that gets "proofread" live: at each swap, a word is struck
// through and its replacement is written above it in the accent. Built for "an old
// complaint that reads like today's": Baudelaire on photography -> AI. Nothing reflows:
// the original words keep their place; replacements sit above them.

export type Swap = { word: string; to: string; at: number };
export type SwapQuoteProps = { lines: string[]; who?: string; swaps?: Swap[]; lineAt?: number[] };

type Box = { w: number; h: number; palette: Palette; t0: number; vertical: boolean };

export const SwapQuote: React.FC<SwapQuoteProps & Box> = ({ lines, who, swaps = [], lineAt, w, h, palette, t0, vertical }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const F = (s: number) => Math.round((s - t0) * fps);
  const pad = vertical ? 44 : 40;
  const size = vertical ? 60 : 50;
  const cardK = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp", easing: EASE.premium });
  const used = new Set<number>();
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: w - pad * 2, background: palette.paper, borderRadius: RADIUS, boxShadow: SHADOW.card,
        padding: vertical ? "54px 56px 44px" : "44px 52px 36px", opacity: cardK, transform: `translateY(${(1 - cardK) * 30}px)` }}>
        <div style={{ position: "relative" }}>
          <span style={{ position: "absolute", left: -size * 0.45, top: -size * 0.1, fontFamily: FONT.serif, fontSize: size * 1.5,
            color: palette.accentInk, lineHeight: 1 }}>“</span>
          {lines.map((ln, li) => {
            const lk = interpolate(frame, [lineAt ? F(lineAt[li]) : 8 + li * 8, (lineAt ? F(lineAt[li]) : 8 + li * 8) + 14], [0, 1], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.calm });
            return (
              <div key={li} style={{ fontFamily: FONT.serif, fontStyle: "italic", fontSize: size, lineHeight: 1.5, color: palette.ink,
                letterSpacing: "-0.01em", opacity: lk }}>
                {ln.split(" ").map((word, wi) => {
                  const bare = word.replace(/[^\p{L}\p{N}'-]/gu, "").toLowerCase();
                  const si = swaps.findIndex((s, k) => !used.has(k) && s.word.toLowerCase() === bare);
                  if (si < 0) return <span key={wi}>{word} </span>;
                  used.add(si);
                  const s = swaps[si];
                  const f0 = F(s.at);
                  const strike = interpolate(frame, [f0 - 4, f0 + 4], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE.move });
                  const pop = spring({ frame: frame - f0, fps, config: SPRING.snap });
                  const trail = word.slice(word.replace(/[^\p{L}\p{N}'-]+$/u, "").length);
                  const core = word.slice(0, word.length - trail.length);
                  return (
                    <React.Fragment key={wi}>
                    <span style={{ position: "relative", display: "inline-block" }}>
                      <span style={{ opacity: 1 - 0.55 * strike }}>{core}</span>
                      <span style={{ position: "absolute", left: -2, right: -2, top: "52%", height: 4, background: palette.accentInk,
                        transform: `scaleX(${strike}) rotate(-2deg)`, transformOrigin: "left", borderRadius: 2 }} />
                      <span style={{ position: "absolute", left: "50%", bottom: "72%", transform: `translateX(-50%) translateY(${(1 - pop) * 12}px)`,
                        opacity: frame >= f0 ? Math.min(1, pop * 1.5) : 0, fontFamily: FONT.sans, fontStyle: "normal", fontWeight: 800,
                        fontSize: size * 0.62, letterSpacing: "-0.02em", color: palette.accentInk, whiteSpace: "nowrap" }}>{s.to}</span>
                      {trail}
                    </span>{" "}
                    </React.Fragment>
                  );
                })}
              </div>
            );
          })}
        </div>
        {who ? (
          <div style={{ marginTop: 22, fontFamily: FONT.sans, fontWeight: 500, fontSize: vertical ? 30 : 26, color: "#4A4A48" }}>{who}</div>
        ) : null}
      </div>
    </div>
  );
};
