import React from "react";
import { continueRender, delayRender, staticFile } from "remotion";

// The look of a film made with the kit. Pass one to <Film theme={...}>; every component reads it.
export type KitTheme = {
  accent: string; // the brand colour: spend it on the opening and the payoff, not in between
  accent2: string; // a second colour for wipes and bursts
  ink: string; // near-black ground
  paper: string; // near-white
  display: string; // heavy display face (uppercase titles, slams)
  displayStretch: number; // font-stretch % for a variable width axis (100 if the face has none)
  serif: string;
  mono: string; // labels, boards, data
};

export const DEFAULT_THEME: KitTheme = {
  accent: "#FF4D2E",
  accent2: "#FFFFFF",
  ink: "#0A0A0D",
  paper: "#F6F1EA",
  display: "Inter",
  displayStretch: 100,
  serif: "Instrument Serif",
  mono: "Geist Mono",
};

export const ThemeContext = React.createContext<KitTheme>(DEFAULT_THEME);
export const useTheme = () => React.useContext(ThemeContext);

// [family, file under public/, weight range, style, stretch range]
export type FontFaceSpec = [string, string, string, string, string];

export const KIT_FONTS: FontFaceSpec[] = [
  ["Inter", "fonts/InterVariable.woff2", "100 900", "normal", "100%"],
  ["Inter", "fonts/InterVariable-Italic.woff2", "100 900", "italic", "100%"],
  ["Geist Mono", "fonts/GeistMono-Variable.woff2", "100 900", "normal", "100%"],
  ["Instrument Serif", "fonts/InstrumentSerif-Regular.ttf", "400", "normal", "100%"],
  ["Instrument Serif", "fonts/InstrumentSerif-Italic.ttf", "400", "italic", "100%"],
];

// Load fonts from public/ before the first frame renders, so renders never depend on the network.
// Call once at module level in the film's entry: loadFonts([...KIT_FONTS, ["Archivo", "fonts/Archivo-wdth.woff2", "100 900", "normal", "62% 125%"]]).
export const loadFonts = (faces: FontFaceSpec[]) => {
  const handle = delayRender("fonts");
  Promise.all(
    faces.map(([family, url, weight, style, stretch]) => {
      const face = new FontFace(family, `url(${staticFile(url)})`, { weight, style, stretch });
      document.fonts.add(face);
      return face.load();
    }),
  ).then(() => continueRender(handle), (e) => { console.error(e); continueRender(handle); });
};
