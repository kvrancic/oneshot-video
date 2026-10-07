#!/usr/bin/env python3
"""Final Cut Pro (and DaVinci Resolve) hand-back: the Premiere timeline as FCPXML 1.10.

  fcpxml.py DIR/out/premiere/<id>.xml [--out <id>.fcpxml]

Reads the FCP7 XML that premiere.py writes and rebuilds it for Final Cut Pro
(File > Import > XML). DaVinci Resolve reads either file (File > Import > Timeline).

  primary storyline  V1, every shot on its original file (gaps where V1 is empty);
                     punch-ins as Transform scale and position, conform off (scale 1 = source pixels)
  lanes 1, 2, ...    V2, V3 (rendered graphics, extra video layers) as connected clips
  lanes -1, -2, ...  A1 voice, A2 room, music beds (a stereo pair becomes one clip)
  chapter markers    one per Premiere marker

Beta: written against the FCPXML 1.10 DTD and validated with it, not yet round-tripped in
Final Cut Pro or Resolve. Report what breaks.
"""
import argparse, json, subprocess, sys
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, quote
from xml.etree import ElementTree as ET


def t(frames, fps):
    """Frames as an FCPXML rational time string."""
    v = Fraction(frames) / fps
    return "0s" if v == 0 else (f"{v.numerator}s" if v.denominator == 1 else f"{v.numerator}/{v.denominator}s")


def tc_start(path):
    """The media's own timecode origin in seconds (camera originals often start at time of day)."""
    try:
        d = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,r_frame_rate:stream_tags=timecode:format_tags=timecode",
                                       "-of", "json", path], capture_output=True, text=True, check=True).stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Fraction(0)
    tags = [s.get("tags", {}).get("timecode") for s in d.get("streams", [])] + [d.get("format", {}).get("tags", {}).get("timecode")]
    tc = next((x for x in tags if x), None)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    if not tc or not v:
        return Fraction(0)
    fps = Fraction(v["r_frame_rate"])
    h, m, s, f = (int(x) for x in tc.replace(";", ":").split(":"))
    return Fraction((h * 3600 + m * 60 + s) * round(fps) + f) / fps  # timecode frames at the media's real rate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xml")
    ap.add_argument("--out")
    args = ap.parse_args()
    src = Path(args.xml)
    seq = ET.parse(src).getroot().find("sequence")
    fps = int(seq.findtext("rate/timebase"))
    vfmt = seq.find("media/video/format/samplecharacteristics")
    W, H = int(vfmt.findtext("width")), int(vfmt.findtext("height"))
    total = int(seq.findtext("duration"))

    # File definitions appear once in FCP7 XML; later uses reference the id.
    files = {}
    for f in seq.iter("file"):
        if f.find("pathurl") is not None:
            files[f.get("id")] = f

    root = ET.Element("fcpxml", version="1.10")
    res = ET.SubElement(root, "resources")
    ET.SubElement(res, "format", id="r0", name=f"FFVideoFormat{H}p{fps}", frameDuration=t(1, fps), width=str(W), height=str(H))
    assets, formats, n = {}, {}, [0]

    def asset(fid):
        if fid in assets:
            return assets[fid]
        f = files[fid]
        path = unquote(f.findtext("pathurl").replace("file://localhost", ""))
        sc = f.find("media/video/samplecharacteristics")
        n[0] += 1
        aid = f"r{n[0]}"
        attrs = {"id": aid, "name": f.findtext("name"), "duration": t(int(f.findtext("duration")), fps),
                 "hasVideo": "1" if sc is not None else "0", "hasAudio": "1" if f.find("media/audio") is not None else "0"}
        start = tc_start(path) if Path(path).exists() else Fraction(0)
        attrs["start"] = t(start * fps, fps)
        if sc is not None:
            size = (sc.findtext("width"), sc.findtext("height"))
            if size not in formats:
                n[0] += 1
                formats[size] = f"r{n[0]}"
                res.insert(len(formats), ET.Element("format", id=formats[size], width=size[0], height=size[1]))
            attrs["format"] = formats[size]
        if attrs["hasAudio"] == "1":
            attrs["audioSources"] = "1"
            attrs["audioChannels"] = f.findtext("media/audio/channelcount") or "2"
            attrs["audioRate"] = "48000"
        a = ET.SubElement(res, "asset", attrs)
        ET.SubElement(a, "media-rep", kind="original-media", src="file://" + quote(path))
        assets[fid] = (aid, start)
        return assets[fid]

    def items(track):
        for ci in track.findall("clipitem"):
            fid = ci.find("file").get("id")
            yield {"name": ci.findtext("name") or "", "start": int(ci.findtext("start")), "end": int(ci.findtext("end")),
                   "in": int(ci.findtext("in")), "fid": fid, "enabled": ci.findtext("enabled") != "FALSE",
                   "channel": int(ci.findtext("sourcetrack/trackindex") or 1), "ci": ci}

    def transform(el, ci):
        """Premiere Basic Motion (scale %, centre as a fraction of the frame from its middle,
        +y down) as FCPXML Transform (scale factor, position in percent of frame height, +y up)."""
        eff = next((e for e in ci.iter("effect") if e.findtext("effectid") == "basic"), None)
        ET.SubElement(el, "adjust-conform", type="none")
        if eff is None:
            return
        p = {x.findtext("parameterid"): x for x in eff.findall("parameter")}
        s = float(p["scale"].findtext("value")) / 100 if "scale" in p else 1.0
        h = float(p["center"].findtext("value/horiz")) if "center" in p else 0.0
        v = float(p["center"].findtext("value/vert")) if "center" in p else 0.0
        ET.SubElement(el, "adjust-transform", position=f"{h * W / H * 100 + 0:.4f} {-v * 100 + 0:.4f}", scale=f"{s:.5f} {s:.5f}")

    lib = ET.SubElement(root, "library")
    ev = ET.SubElement(lib, "event", name=seq.findtext("name"))
    proj = ET.SubElement(ev, "project", name=seq.findtext("name"))
    sq = ET.SubElement(proj, "sequence", format="r0", duration=t(total, fps), tcStart="0s", tcFormat="NDF", audioLayout="stereo", audioRate="48k")
    spine = ET.SubElement(sq, "spine")

    vtracks = seq.findall("media/video/track")
    atracks = seq.findall("media/audio/track")

    # Primary storyline: V1, with gaps so every clip sits at its timeline frame.
    prim, at = [], 0  # (element, timeline offset, source start frames)
    for c in sorted(items(vtracks[0]), key=lambda c: c["start"]) if vtracks else []:
        if c["start"] > at:
            g = ET.SubElement(spine, "gap", name="Gap", offset=t(at, fps), start="0s", duration=t(c["start"] - at, fps))
            prim.append((g, at, 0))
        aid, st = asset(c["fid"])
        s0 = st * fps + c["in"]
        el = ET.SubElement(spine, "asset-clip", ref=aid, name=c["name"], offset=t(c["start"], fps), start=t(s0, fps),
                           duration=t(c["end"] - c["start"], fps), srcEnable="video", tcFormat="NDF")
        if not c["enabled"]:
            el.set("enabled", "0")
        transform(el, c["ci"])
        prim.append((el, c["start"], s0))
        at = c["end"]
    ends = [c["end"] for tr in vtracks + atracks for c in items(tr)] + [total]
    if max(ends) > at:
        g = ET.SubElement(spine, "gap", name="Gap", offset=t(at, fps), start="0s", duration=t(max(ends) - at, fps))
        prim.append((g, at, 0))

    def parent(frame):
        for el, off, s0 in reversed(prim):
            if off <= frame:
                return el, off, s0
        return prim[0]

    # Connected clips: offsets are in the parent's own time (its start + distance into it).
    def connect(c, lane, video):
        el, off, s0 = parent(c["start"])
        aid, st = asset(c["fid"])
        x = ET.Element("asset-clip", ref=aid, lane=str(lane), name=c["name"], offset=t(s0 + c["start"] - off, fps),
                       start=t(st * fps + c["in"], fps), duration=t(c["end"] - c["start"], fps),
                       srcEnable="video" if video else "audio", tcFormat="NDF")
        if not c["enabled"]:
            x.set("enabled", "0")
        if video:
            transform(x, c["ci"])
        else:
            x.set("audioRole", "dialogue" if lane >= -2 else "music")
        # anchored items go before markers
        kids = list(el)
        idx = next((k for k, e in enumerate(kids) if e.tag in ("marker", "chapter-marker")), len(kids))
        el.insert(idx, x)

    for k, tr in enumerate(vtracks[1:], 1):
        for c in items(tr):
            connect(c, k, True)
    lane = 0
    for tr in atracks:
        cs = [c for c in items(tr) if c["channel"] == 1]  # the right channel of a stereo pair is the same clip
        if not cs:
            continue
        lane -= 1
        for c in cs:
            connect(c, lane, False)

    for mk in seq.findall("marker"):
        f = int(mk.findtext("in"))
        el, off, s0 = parent(f)
        ET.SubElement(el, "chapter-marker", start=t(s0 + f - off, fps), duration=t(1, fps), value=mk.findtext("name") or "chapter")

    ET.indent(root)
    out = Path(args.out) if args.out else src.with_suffix(".fcpxml")
    out.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(root, encoding="unicode") + "\n")
    print(f"-> {out}\n   {sum(1 for e in prim if e[0].tag == 'asset-clip')} shots in the storyline, "
          f"{len(list(sq.iter('asset-clip'))) - sum(1 for e in prim if e[0].tag == 'asset-clip')} connected clips, "
          f"{len(list(sq.iter('chapter-marker')))} chapter markers; {total / fps / 60:.1f} min")


if __name__ == "__main__":
    sys.exit(main())
