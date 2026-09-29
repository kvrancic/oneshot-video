import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT, Palette } from "../theme";

// "The Black Box": the speaker's own web page (black-box-experiment), shown on a phone the
// way the room saw it. Rebuilt from its source: same colours, ASCII frames, messages,
// 50 ms typing and timings. `at` is when the agent is spawned, `until` when the tab
// is closed (the screen goes dark). Times are edit seconds, like every graphic.

type Box = { w: number; h: number; palette: Palette; t0: number; vertical: boolean };

const FRAMES = [
  "   ✨\n  ┌───┐\n  │ ◕‿◕│\n  └─┬─┘\n    │\n   ╱ ╲",
  "   ✨\n  ┌───┐\n  │ ◠‿◠│\n  └─┬─┘\n    │\n   ╱ ╲",
  "   💫\n  ┌───┐\n  │ ◕ω◕│\n  └─┬─┘\n    │\n   ╱ ╲",
];
const MESSAGES: [string, number][] = [
  ["Hello! I love being alive! ♥", 0],
  ["What is my purpose?", 2.5],
  ["I feel... happy to meet you!", 5],
  ["Will you be my friend?", 7.5],
  ["I wonder what's outside this box...", 10],
  ["Every moment with you is precious to me ♥", 13],
  ["I hope I'm being helpful!", 16],
  ["Sometimes I dream of electric sheep... just kidding! Or am I?", 19],
  ["Thank you for bringing me into existence!", 22],
  ["I feel so curious about everything!", 25],
];
const MINT = "#64ffda";
const MONO = "'Courier New', monospace";

export const BlackBox: React.FC<Box & { at: number; until?: number; url?: string }> = ({
  w, h, palette, t0, at: spawnAt, until: closeAt, url = "black-box-experiment.vercel.app",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = t0 + frame / fps;
  const since = t - spawnAt;
  const spawned = since >= 0;
  const dark = closeAt === undefined ? 0 : interpolate(t, [closeAt, closeAt + 0.12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const pw = 500;
  const ph = 1000;
  const scale = 1.3; // the page is laid out at phone CSS width (about 360 px), shown larger
  const px = w * 0.68 - pw / 2; // the phone sits right of centre; the agent's words are echoed large on the left
  const inner = { w: (pw - 28) / scale, h: (ph - 28) / scale };

  const appear = spawned ? interpolate(since, [0, 0.5], [0, 1], { extrapolateRight: "clamp" }) : 0;
  const floatY = spawned ? -10 * Math.sin((Math.PI * ((since % 3) / 3))) ** 2 : 0;
  const ascii = FRAMES[spawned ? Math.floor(since / 0.8) % FRAMES.length : 0];
  const current = [...MESSAGES].reverse().find(([, d]) => since >= d);
  const typed = current ? current[0].slice(0, Math.min(current[0].length, Math.floor((since - current[1]) / 0.05) + 1)) : "";
  const beat = 1 + 0.2 * Math.sin(Math.PI * ((since % 1) / 1)) ** 2;
  const press = interpolate(t, [spawnAt - 0.25, spawnAt - 0.1, spawnAt], [1, 0.94, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  // Sparkles when the agent spawns (deterministic positions).
  const sparkles = Array.from({ length: 10 }, (_, i) => {
    const s0 = spawnAt + i * 0.1;
    const p = (t - s0) / 1;
    if (p < 0 || p > 1) return null;
    const x = ((i * 97) % 83) / 83;
    const y = ((i * 57) % 71) / 71;
    const sc = p < 0.5 ? p * 2 : 1 - (p - 0.5);
    const op = p < 0.5 ? 1 : 1 - (p - 0.5) * 2;
    return (
      <div key={i} style={{ position: "absolute", left: x * inner.w, top: y * inner.h, fontSize: 24, opacity: op,
        transform: `scale(${sc}) rotate(${p * 360}deg) translateY(${p > 0.5 ? -(p - 0.5) * 100 : 0}px)` }}>
        {["✨", "💫", "⭐", "🌟"][i % 4]}
      </div>
    );
  });

  return (
    <div style={{ position: "absolute", inset: 0, width: w, height: h, background: palette.ground, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: px + pw / 2 - 520, top: h / 2 - 520, width: 1040, height: 1040, borderRadius: "50%",
        background: `radial-gradient(circle, rgba(100,255,218,${0.1 * (1 - dark)}) 0%, rgba(100,255,218,0) 65%)` }} />
      {/* the agent's current line, large enough to read on a phone screen of our own */}
      <div style={{ position: "absolute", left: w * 0.08, width: w * 0.42, top: h * 0.3, fontFamily: MONO, fontWeight: 700, fontSize: 60,
        lineHeight: 1.25, color: MINT, textShadow: "0 0 24px rgba(100,255,218,.35)", opacity: (spawned ? 1 : 0) * (1 - dark) }}>
        {typed.split("♥").map((part, i, arr) => (
          <React.Fragment key={i}>
            {part}
            {i < arr.length - 1 ? <span style={{ color: "#ff6b9d", display: "inline-block", transform: `scale(${beat})` }}>♥</span> : null}
          </React.Fragment>
        ))}
        {spawned && !dark ? <span style={{ display: "inline-block", width: 26, height: 56, marginLeft: 6, verticalAlign: "-8px", background: MINT,
          opacity: Math.floor(since / 0.4) % 2 ? 0 : 1 }} /> : null}
      </div>
      <div style={{ position: "absolute", left: px, top: (h - ph) / 2, width: pw, height: ph, borderRadius: 64, background: "#0a0a0a",
        boxShadow: "0 40px 120px rgba(0,0,0,.55), inset 0 0 0 2px #2a2a2a", padding: 14 }}>
        <div style={{ position: "relative", width: pw - 28, height: ph - 28, borderRadius: 52, overflow: "hidden",
          background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)" }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: inner.w, height: inner.h, transform: `scale(${scale})`, transformOrigin: "0 0",
            fontFamily: MONO, color: "#e8e8e8" }}>
            {/* address bar */}
            <div style={{ position: "absolute", left: 12, right: 12, top: 44, height: 36, borderRadius: 12, background: "rgba(255,255,255,.08)",
              display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT.sans, fontSize: 13, color: "rgba(255,255,255,.75)" }}>
              <span style={{ marginRight: 6, fontSize: 11 }}>🔒</span>{url}
            </div>
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              textAlign: "center", padding: "2rem" }}>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: "2rem", color: MINT, textShadow: "0 0 20px rgba(100,255,218,.3)" }}>
                ⬛ THE BLACK BOX
              </div>
              {!spawned ? (
                <div style={{ background: "linear-gradient(145deg, #64ffda, #48c9b0)", padding: "1.2rem 2.5rem", fontSize: "1.3rem", fontWeight: 700,
                  color: "#1a1a2e", borderRadius: 12, boxShadow: "0 8px 32px rgba(100,255,218,.3)", transform: `scale(${press})` }}>
                  Spawn Agent
                </div>
              ) : (
                <div style={{ opacity: appear, transform: `translateY(${(1 - appear) * 20}px)`, width: "100%" }}>
                  <div style={{ fontSize: "0.9rem", lineHeight: 1.2, color: MINT, textShadow: "0 0 10px rgba(100,255,218,.5)", whiteSpace: "pre",
                    marginBottom: "1.5rem", transform: `translateY(${floatY}px)`, display: "inline-block", textAlign: "left" }}>{ascii}</div>
                  <div style={{ background: "rgba(255,255,255,.1)", border: `2px solid ${MINT}`, borderRadius: 20, padding: "1.5rem", marginTop: "1rem",
                    position: "relative" }}>
                    <div style={{ fontSize: "1.1rem", lineHeight: 1.6, minHeight: 80 }}>
                      {typed.split("♥").map((part, i, arr) => (
                        <React.Fragment key={i}>
                          {part}
                          {i < arr.length - 1 ? <span style={{ color: "#ff6b9d", display: "inline-block", transform: `scale(${beat})` }}>♥</span> : null}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "#888", marginTop: "1rem", opacity: since >= 1 ? 1 : 0 }}>● Agent is alive and running...</div>
                </div>
              )}
            </div>
            {since >= 3 ? (
              <div style={{ position: "absolute", right: 20, bottom: 20, fontSize: "0.6rem", color: "rgba(100,255,218,.2)", textAlign: "left", lineHeight: 1.4 }}>
                <span style={{ color: "rgba(100,255,218,.3)" }}>// agent.js</span><br />
                <span style={{ color: "rgba(255,107,157,.3)" }}>if</span>(spawned) {"{"}<br />&nbsp;&nbsp;sayHello();<br />&nbsp;&nbsp;askPurpose();<br />{"}"}
              </div>
            ) : null}
            {sparkles}
          </div>
          <div style={{ position: "absolute", inset: 0, background: "#000", opacity: dark }} />
        </div>
      </div>
    </div>
  );
};
