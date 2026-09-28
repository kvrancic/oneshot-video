import { measureText } from "@remotion/layout-utils";
import { FONT } from "../theme";
import type { Preset } from "./presets";

// A caption token in EDIT seconds (render.py maps source time to edit time).
export type Token = {
  text: string;
  start: number;
  end: number;
  emph?: "accent" | "serif";
  speaker?: string; // "A" | "B" for LEDGER
  breakAfter?: boolean; // force a page break after this word (planner's choice)
};

export type LaidWord = {
  text: string;
  start: number;
  end: number;
  emph?: "accent" | "serif";
  x: number; // left edge inside the block
  line: number;
  width: number;
  fontSize: number;
  family: string;
  italic: boolean;
  weight: number;
};

export type Page = {
  start: number; // first word start (seconds, edit time)
  end: number; // last word end
  showFrom: number; // with lead
  showTo: number; // with hold, clipped by the next page
  words: LaidWord[];
  lineWidths: number[];
  width: number;
  height: number;
  lineHeightPx: number;
  speaker?: string;
};

const CLAUSE_OPENERS = new Set([
  "but", "so", "and", "because", "which", "that", "then", "when", "while", "if", "or", "although", "however",
]);

const cased = (t: string, mode: Preset["textCase"], first: boolean) => {
  if (mode === "lower") return t.toLowerCase();
  if (mode === "sentence" && first) return t.charAt(0).toUpperCase() + t.slice(1);
  return t;
};

// Group tokens into pages on breath and clause, never on a fixed word count alone.
export const groupPages = (tokens: Token[], p: Preset): Token[][] => {
  const pages: Token[][] = [];
  let cur: Token[] = [];
  let chars = 0;
  const flush = () => {
    if (cur.length) pages.push(cur);
    cur = [];
    chars = 0;
  };
  tokens.forEach((t, i) => {
    const prev = tokens[i - 1];
    const gapMs = prev ? (t.start - prev.end) * 1000 : 0;
    const bare = t.text.replace(/[^\p{L}\p{N}']/gu, "").toLowerCase();
    if (cur.length) {
      const dur = (t.end - cur[0].start) * 1000;
      const prevEndsSentence = /[.!?]["')\]]?$/.test(prev.text);
      const prevEndsClause = /[,;:]$/.test(prev.text);
      const tooLong = cur.length >= p.chunk.maxWords || chars + t.text.length + 1 > p.chunk.maxChars * p.chunk.maxLines;
      const speakerChange = t.speaker !== undefined && t.speaker !== prev.speaker;
      if (
        prev.breakAfter ||
        speakerChange ||
        gapMs >= p.chunk.breakOnSilenceMs ||
        prevEndsSentence ||
        tooLong ||
        (dur > p.chunk.combineMs && (prevEndsClause || CLAUSE_OPENERS.has(bare))) ||
        dur > p.chunk.combineMs * 1.8
      ) {
        flush();
      }
    }
    cur.push(t);
    chars += t.text.length + 1;
  });
  flush();
  // No orphan one-word pages glued to a longer thought, unless the preset is word-by-word.
  if (p.chunk.maxWords > 2) {
    for (let i = pages.length - 1; i > 0; i--) {
      const pg = pages[i];
      const before = pages[i - 1];
      const gap = pg[0].start - before[before.length - 1].end;
      const endsSentence = /[.!?]["')\]]?$/.test(before[before.length - 1].text);
      if (pg.length === 1 && gap < 0.25 && !endsSentence && before.length < p.chunk.maxWords + 1 &&
          pg[0].speaker === before[0].speaker) {
        before.push(...pg);
        pages.splice(i, 1);
      }
    }
  }
  return pages;
};

const measure = (text: string, family: string, size: number, weight: number, italic: boolean, trackingEm: number) =>
  measureText({
    text,
    fontFamily: family,
    fontSize: size,
    fontWeight: weight,
    letterSpacing: `${trackingEm}em`,
    additionalStyles: italic ? { fontStyle: "italic" } : undefined,
    validateFontIsLoaded: false,
  }).width;

export const layoutPages = (
  tokens: Token[],
  p: Preset,
  vertical: boolean,
  maxWidth: number,
  sentenceStartIdx: Set<number>,
): Page[] => {
  const size = vertical ? p.size.v : p.size.h;
  const baseFamily = p.family === "serif" ? FONT.serif : FONT.sans;
  const baseItalic = !!p.italic;
  const lineHeightPx = Math.round(size * p.lineHeight);
  // A lone space measures short once tracking is negative; use the gap inside a word pair.
  const spaceW = Math.max(
    measure("a a", baseFamily, size, p.weight, baseItalic, p.tracking) - measure("aa", baseFamily, size, p.weight, baseItalic, p.tracking),
    size * 0.26,
  );
  const groups = groupPages(tokens, p);
  const tokenIndex = new Map(tokens.map((t, i) => [t, i]));
  const charW = size * (p.family === "serif" ? 0.36 : p.weight >= 700 ? 0.5 : 0.47);
  const measureCap = Math.min(maxWidth, p.chunk.maxChars * charW);

  const pages: Page[] = groups.map((g) => {
    const words = g.map((t) => {
      const idx = tokenIndex.get(t)!;
      const serif = t.emph === "serif" && p.emphasis !== "none";
      const family = serif ? FONT.serif : baseFamily;
      const italic = serif ? true : baseItalic;
      const weight = serif ? 400 : p.weight;
      const fontSize = serif ? Math.round(size * p.emphasisScale) : size;
      const text = cased(t.text, p.textCase, sentenceStartIdx.has(idx));
      // Reserve the width of the heaviest state so nothing reflows when a word lights up.
      const width = measure(text, family, fontSize, weight, italic, serif ? 0 : p.tracking);
      return { t, text, family, italic, weight, fontSize, width };
    });

    // Line breaking: one line if it fits, else the most balanced split (no one-word orphan).
    const total = words.reduce((s, w) => s + w.width, 0) + spaceW * (words.length - 1);
    let breaks: number[] = [];
    if (total > measureCap && words.length > 1) {
      if (p.chunk.maxLines >= 2) {
        let best = -1;
        let bestScore = Infinity;
        for (let k = 1; k < words.length; k++) {
          const w1 = words.slice(0, k).reduce((s, w) => s + w.width, 0) + spaceW * (k - 1);
          const w2 = words.slice(k).reduce((s, w) => s + w.width, 0) + spaceW * (words.length - k - 1);
          const over = Math.max(0, w1 - maxWidth) + Math.max(0, w2 - maxWidth);
          // Prefer breaking after punctuation or before a clause opener.
          const bonus = /[,;:]$/.test(words[k - 1].text) || CLAUSE_OPENERS.has(words[k].text.toLowerCase()) ? 0.85 : 1;
          const orphan = k === 1 || k === words.length - 1 ? 1.4 : 1;
          const score = (Math.max(w1, w2) + over * 10) * bonus * orphan;
          if (score < bestScore) {
            bestScore = score;
            best = k;
          }
        }
        breaks = [best];
        // Three-line presets: greedy for anything still too wide.
        if (p.chunk.maxLines >= 3) {
          const w2 = words.slice(best).reduce((s, w) => s + w.width, 0) + spaceW * (words.length - best - 1);
          if (w2 > maxWidth) {
            let acc = 0;
            for (let k = best; k < words.length; k++) {
              acc += words[k].width + (k > best ? spaceW : 0);
              if (acc > maxWidth * 0.95 && k > best) {
                breaks.push(k);
                break;
              }
            }
          }
        }
      }
    }

    const laid: LaidWord[] = [];
    const lineWidths: number[] = [];
    let line = 0;
    let x = 0;
    words.forEach((w, i) => {
      if (breaks.includes(i)) {
        lineWidths.push(x - spaceW);
        line += 1;
        x = 0;
      }
      laid.push({
        text: w.text,
        start: w.t.start,
        end: w.t.end,
        emph: p.emphasis === "none" ? undefined : w.t.emph,
        x,
        line,
        width: w.width,
        fontSize: w.fontSize,
        family: w.family,
        italic: w.italic,
        weight: w.weight,
      });
      x += w.width + spaceW;
    });
    lineWidths.push(x - spaceW);
    const width = Math.max(...lineWidths);
    return {
      start: g[0].start,
      end: g[g.length - 1].end,
      showFrom: g[0].start - p.leadMs / 1000,
      showTo: g[g.length - 1].end + p.holdMs / 1000,
      words: laid,
      lineWidths,
      width,
      height: lineHeightPx * lineWidths.length,
      lineHeightPx,
      speaker: g[0].speaker,
    };
  });

  // Pages never overlap; a page yields 2 frames (at 30 fps) before the next one leads in.
  for (let i = 0; i < pages.length - 1; i++) {
    const next = pages[i + 1];
    pages[i].showTo = Math.min(pages[i].showTo, next.showFrom - 0.001);
    pages[i].showTo = Math.max(pages[i].showTo, Math.min(pages[i].showFrom + 0.5, next.showFrom - 0.001));
    if (p.clearOnPauseMs && next.start - pages[i].end > p.clearOnPauseMs / 1000) {
      pages[i].showTo = Math.min(pages[i].showTo, pages[i].end + 0.5);
    }
  }
  return pages;
};
