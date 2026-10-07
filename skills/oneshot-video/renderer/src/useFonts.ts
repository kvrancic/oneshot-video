import { useEffect, useState } from "react";
import { continueRender, delayRender } from "remotion";
import { fontsReady } from "./fonts";

// Hold the frame until the local fonts are in, so text is measured with the real metrics.
export const useFontsReady = () => {
  const [handle] = useState(() => delayRender("fonts"));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    fontsReady.then(() => {
      setReady(true);
      continueRender(handle);
    });
  }, [handle]);
  return ready;
};
