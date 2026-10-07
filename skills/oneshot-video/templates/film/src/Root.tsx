import { Composition } from "remotion";
import { Layer } from "./kit";
import { Main } from "./Main";
import { FPS, H, T, W } from "./timing";

// One composition; the layer prop renders the film or one editable layer of it (scripts/film_layers.py).
export const RemotionRoot = () => (
  <Composition id="Film" component={Main} defaultProps={{ layer: "full" as Layer }} durationInFrames={Math.round(T.total * FPS)} fps={FPS} width={W} height={H} />
);
