import React from "react";
import { Composition } from "remotion";
import { Clip, ClipProps } from "./Clip";
import { CaptionLab, CaptionLabProps } from "./lab/CaptionLab";
import { DIMS } from "./theme";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Clip"
        component={Clip}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{} as ClipProps}
        calculateMetadata={({ props }) => ({
          durationInFrames: props.durationInFrames ?? 300,
          fps: props.fps ?? 30,
          width: DIMS[props.format ?? "9x16"].w,
          height: DIMS[props.format ?? "9x16"].h,
        })}
      />
      <Composition
        id="CaptionLab"
        component={CaptionLab}
        durationInFrames={30 * 23}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ preset: "verdict", format: "9x16", palette: "paper", tokens: [] } as CaptionLabProps}
        calculateMetadata={({ props }) =>
          props.format === "16x9" ? { width: 1920, height: 1080 } : { width: 1080, height: 1920 }
        }
      />
    </>
  );
};
