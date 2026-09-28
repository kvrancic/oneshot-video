import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Local OFL fonts (public/fonts), so renders never depend on the network.
const fonts = [
  { family: "Inter", url: "fonts/InterVariable.woff2", weight: "100 900", style: "normal" },
  { family: "Inter", url: "fonts/InterVariable-Italic.woff2", weight: "100 900", style: "italic" },
  { family: "Instrument Serif", url: "fonts/InstrumentSerif-Regular.ttf", weight: "400", style: "normal" },
  { family: "Instrument Serif", url: "fonts/InstrumentSerif-Italic.ttf", weight: "400", style: "italic" },
  { family: "Geist Mono", url: "fonts/GeistMono-Variable.woff2", weight: "100 900", style: "normal" },
] as const;

export const fontsReady: Promise<unknown> = Promise.all(
  fonts.map((f) =>
    loadFont({ family: f.family, url: staticFile(f.url), weight: f.weight, style: f.style }),
  ),
);
