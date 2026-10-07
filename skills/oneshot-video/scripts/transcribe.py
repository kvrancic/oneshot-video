#!/usr/bin/env python3
"""Local, offline, word-level transcription from two models that check each other.

Whisper large-v3-turbo (whisper.cpp on Metal) gives the words: it is the better
listener in a reverberant room and takes a vocabulary prompt (names, products).
Parakeet TDT 0.6B v3 (ONNX on CPU) gives the timing: its token timestamps sit on
the actual onsets, where Whisper's run 0.1 to 0.3 s late. The two word streams are
aligned; matched words take Parakeet's times, unmatched Whisper words are spread
over the matching gap. Words the models disagree on are marked `"?": true`; those
are the ones to proofread. Fillers only Parakeet heard ("uh", "um") are kept in
`fillers` so the editor can cut them.

  transcribe.py SOURCE --out work/<key>/transcript [--from S --to S]
                [--context "A lecture at MIT on AI agents. It mentions Sam Altman and Anthropic."]
                [--fix "Entropic=Anthropic"] [--fix "Yann LeCoult=Yann LeCun"]

Outputs <out>.words.json and <out>.transcript.txt (one sentence per line:
[h:mm:ss.s #wordindex] text, with ? after doubtful words).
"""
import argparse, difflib, json, os, re, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
WHISPER_MODEL = MODELS / "ggml-large-v3-turbo-q8_0.bin"
WHISPER_VAD = MODELS / "ggml-silero-v5.1.2.bin"
HANDY = Path.home() / "Library/Application Support/com.pais.handy/models/parakeet-tdt-0.6b-v3-int8"
FRAME = 0.08  # Parakeet encoder frame
FILLERS = {"uh", "um", "uhm", "erm", "er", "ah", "hmm", "mm", "mhm"}


def fmt(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:04.1f}"


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


# ---------------------------------------------------------------- whisper

def run_whisper(wav, prompt, threads=8):
    out = wav + ".whisper"
    cmd = ["whisper-cli", "-m", str(WHISPER_MODEL), "-f", wav, "-l", "en", "-t", str(threads), "-nfa",
           "--dtw", "large.v3.turbo", "-ojf", "-of", out, "-np"]
    if WHISPER_VAD.exists():
        cmd += ["--vad", "-vm", str(WHISPER_VAD), "-vsd", "300", "-vp", "200"]
    if prompt:
        cmd += ["--prompt", prompt]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    data = json.loads(Path(out + ".json").read_text())
    words = []
    for seg in data["transcription"]:
        for tok in seg["tokens"]:
            txt = tok["text"]
            if txt.startswith("[_") or txt.startswith("<|"):
                continue
            t = tok.get("t_dtw", -1)
            t = t / 100 if t is not None and t >= 0 else tok["offsets"]["from"] / 1000
            if txt.startswith(" ") or not words:
                words.append({"w": txt.strip(), "s": t, "p": [tok.get("p", 1.0)]})
            else:
                words[-1]["w"] += txt
                words[-1]["p"].append(tok.get("p", 1.0))
    for w in words:
        w["p"] = round(float(min(w["p"])), 3)
    return [w for w in words if w["w"]]


# ---------------------------------------------------------------- parakeet

_PK = {}


def _parakeet(vad):
    import onnx_asr

    if vad not in _PK:
        model_dir = os.environ.get("CUTROOM_ASR_MODEL") or (str(HANDY) if HANDY.exists() else None)
        asr = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", model_dir, quantization="int8",
                                  providers=["CPUExecutionProvider"])
        _PK[vad] = (asr.with_vad(onnx_asr.load_vad("silero")) if vad else asr).with_timestamps()
    return _PK[vad]


def _pk_words(r, off):
    start = getattr(r, "start", 0.0) or 0.0
    end = getattr(r, "end", None)
    seg = []
    for tok, ts in zip(r.tokens, r.timestamps):
        t = off + start + ts
        if tok.startswith(" ") or not seg:
            seg.append({"w": tok.strip(), "s": t, "last": t})
        else:
            seg[-1]["w"] += tok
            seg[-1]["last"] = t
    seg_end = off + end if end is not None else (seg[-1]["last"] + 3 * FRAME if seg else off)
    for j, w in enumerate(seg):
        nxt = seg[j + 1]["s"] if j + 1 < len(seg) else seg_end
        e = max(w.pop("last") + 2 * FRAME, w["s"] + FRAME)
        if nxt - e < 0.12 or e > nxt:
            e = nxt
        w["e"] = min(e, seg_end + 0.05)
    return [w for w in seg if w["w"]]


def run_parakeet(wav, chunk_s=600):
    rec = _parakeet(vad=True)
    audio, sr = sf.read(wav, dtype="float32")
    words = []
    tmp = wav + ".chunk.wav"
    step = int(chunk_s * sr)
    for i in range(0, len(audio), step):
        sf.write(tmp, audio[i:i + step], sr)
        for r in rec.recognize(tmp):
            words.extend(_pk_words(r, i / sr))
    return words


def realign(words, wav):
    """Re-time every run of words Parakeet's long pass did not confirm by running
    Parakeet (no VAD) on just that stretch of audio. The long pass sometimes drops a
    region; interpolated times there can be a second off, which ruins a cut."""
    audio, sr = sf.read(wav, dtype="float32")
    rec = _parakeet(vad=False)
    tmp = wav + ".win.wav"
    n = len(words)
    k = 0
    fixed = 0
    while k < n:
        if words[k]["src"] == "both":
            k += 1
            continue
        j = k
        while j + 1 < n and words[j + 1]["src"] != "both":
            j += 1
        # Give Parakeet about 1.5 s of confirmed speech on each side to hear in context.
        c0, c1 = k, j
        while c0 > 0 and words[k]["s"] - words[c0 - 1]["s"] < 1.5:
            c0 -= 1
        while c1 + 1 < n and words[c1 + 1]["e"] - words[j]["e"] < 1.5:
            c1 += 1
        lo = words[c0]["s"] - 0.15
        hi = words[c1]["e"] + 0.15
        if 0 < hi - lo < 30:
            sf.write(tmp, audio[int(max(lo, 0) * sr):int(hi * sr)], sr)
            pk = _pk_words(rec.recognize(tmp), max(lo, 0))
            ctx = list(range(c0, c1 + 1))
            a = [norm(words[i]["w"]) for i in ctx]
            b = [norm(w["w"]) for w in pk]
            sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == "equal":
                    for d in range(i2 - i1):
                        wi = ctx[i1 + d]
                        if words[wi]["src"] != "both":
                            words[wi]["s"], words[wi]["e"] = pk[j1 + d]["s"], pk[j1 + d]["e"]
                            words[wi]["src"] = "realigned"
                            words[wi]["?"] = False
                            fixed += 1
                elif tag == "replace" and j2 > j1:
                    s0, e0 = pk[j1]["s"], pk[j2 - 1]["e"]
                    idx = [ctx[i] for i in range(i1, i2) if words[ctx[i]]["src"] != "both"]
                    if idx:
                        lens = np.array([max(len(words[i]["w"]), 2) for i in idx], float)
                        edges = s0 + (e0 - s0) * np.concatenate([[0], np.cumsum(lens) / lens.sum()])
                        for d, wi in enumerate(idx):
                            words[wi]["s"], words[wi]["e"] = float(edges[d]), float(edges[d + 1])
                            words[wi]["src"] = "realigned~"
                            fixed += 1
        k = j + 1
    for i in range(1, n):
        if words[i]["s"] < words[i - 1]["s"]:
            words[i]["s"] = words[i - 1]["s"]
        if words[i - 1]["e"] > words[i]["s"]:
            words[i - 1]["e"] = words[i]["s"]
        if words[i]["e"] <= words[i]["s"]:
            words[i]["e"] = words[i]["s"] + 0.05
    return fixed


def drop_repeats(words, min_len=3):
    """Whisper sometimes writes a phrase twice; the copy Parakeet never heard gets squeezed to
    zero length beside the real one and shows up as a duplicate sentence and as caption words
    with no time. Where a run of min_len+ words repeats right next to itself, drop the copy with
    no confirmed word, or (both unconfirmed) the one with almost no duration. A real repeat
    ("I want Dave. I want Dave.") is heard by both models and stays."""
    def weak(run):
        confirmed = sum(w["src"] in ("both", "realigned") for w in run)
        dur = sum(w["e"] - w["s"] for w in run) / len(run)
        return confirmed == 0 or dur < 0.08, (confirmed, dur)
    keep = [True] * len(words)
    i = 0
    while i < len(words):
        hit = False
        for L in range(min(12, (len(words) - i) // 2), min_len - 1, -1):
            a, b = words[i:i + L], words[i + L:i + 2 * L]
            if [norm(w["w"]) for w in a] != [norm(w["w"]) for w in b] or not all(keep[i:i + 2 * L]):
                continue
            (wa, sa), (wb, sb) = weak(a), weak(b)
            if not (wa or wb):
                continue
            lo = i + L if (wb and (not wa or sb <= sa)) else i
            for k in range(lo, lo + L):
                keep[k] = False
            i += 2 * L
            hit = True
            break
        if not hit:
            i += 1
    return [w for w, k in zip(words, keep) if k], keep.count(False)


# ---------------------------------------------------------------- merge

def merge(wh, pk):
    a = [norm(w["w"]) for w in wh]
    b = [norm(w["w"]) for w in pk]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = [None] * len(wh)
    used_pk = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                p = pk[j1 + k]
                out[i1 + k] = {"w": wh[i1 + k]["w"], "s": p["s"], "e": p["e"], "src": "both"}
                used_pk.add(j1 + k)
        elif tag in ("replace", "delete"):  # delete = words only Whisper heard
            n = i2 - i1
            if n == 0:
                continue
            if tag == "replace" and j2 > j1:
                s, e = pk[j1]["s"], pk[j2 - 1]["e"]
                used_pk.update(range(j1, j2))
                src = "whisper"
            else:
                s, e = wh[i1]["s"], (wh[i2]["s"] if i2 < len(wh) else wh[i2 - 1]["s"] + 0.4)
                src = "whisper-only"
            lens = np.array([max(len(wh[k]["w"]), 2) for k in range(i1, i2)], float)
            edges = s + (e - s) * np.concatenate([[0], np.cumsum(lens) / lens.sum()])
            for k in range(n):
                out[i1 + k] = {"w": wh[i1 + k]["w"], "s": float(edges[k]), "e": float(edges[k + 1]), "src": src}
    fillers = [{"w": pk[j]["w"], "s": round(pk[j]["s"], 3), "e": round(pk[j]["e"], 3)}
               for j in range(len(pk)) if j not in used_pk and norm(pk[j]["w"]) in FILLERS]
    # Whisper-only words right after a gap where Parakeet heard nothing are the
    # classic hallucination (text in silence); keep them but mark them.
    for k, w in enumerate(out):
        w["?"] = w["src"] == "whisper-only" or (w["src"] != "both" and wh[k]["p"] < 0.5)
    # Monotonic and non-overlapping.
    for k in range(1, len(out)):
        if out[k]["s"] < out[k - 1]["s"]:
            out[k]["s"] = out[k - 1]["s"]
        if out[k - 1]["e"] > out[k]["s"]:
            out[k - 1]["e"] = out[k]["s"]
        if out[k]["e"] <= out[k]["s"]:
            out[k]["e"] = out[k]["s"] + 0.05
    return out, fillers


def apply_fixes(words, fixes):
    table = dict(f.split("=", 1) for f in fixes)
    multi = {k: v for k, v in table.items() if " " in k}
    for w in words:
        core = re.sub(r"^[\"'(\[]+|[\"')\].,!?;:]+$", "", w["w"])
        if core in table:
            w["w"] = w["w"].replace(core, table[core])
    for k, v in multi.items():  # phrase fixes: "Yann LeCoult=Yann LeCun"
        ks, vs = k.split(), v.split()
        for i in range(len(words) - len(ks) + 1):
            if [re.sub(r"[.,!?;:]$", "", words[i + j]["w"]) for j in range(len(ks))] == ks:
                tail = re.search(r"[.,!?;:]$", words[i + len(ks) - 1]["w"])
                for j in range(len(ks)):
                    words[i + j]["w"] = vs[j] if j < len(vs) else ""
                if tail:
                    words[i + len(ks) - 1]["w"] += tail.group(0)
    return [w for w in words if w["w"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--out", required=True)
    ap.add_argument("--from", dest="a", type=float)
    ap.add_argument("--to", dest="b", type=float)
    ap.add_argument("--context", default="", help='one or two plain sentences naming the talk, people and terms, '
                    'e.g. "A lecture at MIT on AI agents. It mentions Sam Altman, Dario Amodei and Anthropic."')
    ap.add_argument("--fix", action="append", default=[], help='"wrong=Right" (word or phrase), repeatable')
    ap.add_argument("--whisper-only", action="store_true")
    ap.add_argument("--stream", type=int, help="audio stream index in SOURCE (the microphone track)")
    ap.add_argument("--offset", type=float, default=0.0,
                    help="SOURCE is a separate recording: its time = picture time + offset (from ingest.py); "
                         "words are written in picture time")
    args = ap.parse_args()

    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="oneshot-asr-")
    wav = os.path.join(tmp, "audio.wav")
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if args.a is not None or args.offset:
        cmd += ["-ss", str(max((args.a or 0) + args.offset, 0))]
    if args.b is not None:
        cmd += ["-t", str(args.b - (args.a or 0))]
    cmd += ["-i", args.source, *(["-map", f"0:a:{args.stream}"] if args.stream is not None else ["-vn"]),
            "-ac", "1", "-ar", "16000", wav]
    subprocess.run(cmd, check=True)
    base = max((args.a or 0.0) + args.offset, 0.0) - args.offset  # picture time of the first sample
    total = sf.info(wav).duration

    prompt = args.context.strip()
    with ThreadPoolExecutor(2) as ex:
        fw = ex.submit(run_whisper, wav, prompt)
        fp = None if args.whisper_only else ex.submit(run_parakeet, wav)
        wh = fw.result()
        print(f"  whisper: {len(wh)} words ({time.time() - t0:.0f}s)", file=sys.stderr)
        pk = fp.result() if fp else []
        if fp:
            print(f"  parakeet: {len(pk)} words ({time.time() - t0:.0f}s)", file=sys.stderr)

    if pk:
        words, fillers = merge(wh, pk)
        fixed = realign(words, wav)
        print(f"  realigned {fixed} words ({time.time() - t0:.0f}s)", file=sys.stderr)
        words, dropped = drop_repeats(words)
        if dropped:
            print(f"  dropped {dropped} words Whisper wrote twice", file=sys.stderr)
        for w in words:  # a word squeezed to no time (often next to applause) has no reliable cut point
            if w["e"] - w["s"] < 0.03:
                w["?"] = True
    else:
        words, fillers = [{"w": w["w"], "s": w["s"], "e": w["s"] + 0.3, "src": "whisper", "?": w["p"] < 0.4}
                          for w in wh], []
        for k in range(len(words) - 1):
            words[k]["e"] = min(words[k]["e"], words[k + 1]["s"])
    words = apply_fixes(words, args.fix)

    for i, w in enumerate(words):
        w["s"] = round(w["s"] + base, 3)
        w["e"] = round(w["e"] + base, 3)
        w["i"] = i
        if re.search(r"[.!?][\"')\]]?$", w["w"]):
            w["eos"] = True
    for i, w in enumerate(words[:-1]):
        gap = words[i + 1]["s"] - w["e"]
        if gap >= 0.35:
            w["pause"] = round(gap, 2)
    for f in fillers:
        f["s"] += base
        f["e"] += base

    agree = sum(w["src"] == "both" for w in words) / max(len(words), 1)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{out}.words.json").write_text(json.dumps({
        "source": str(Path(args.source).resolve()), "from": base, "duration": round(total, 3),
        "asr": "whisper-large-v3-turbo text + parakeet-tdt-0.6b-v3 timing", "agreement": round(agree, 3),
        "context": args.context, "words": words, "fillers": fillers}, ensure_ascii=False))

    lines, cur = [], []
    for w in words:
        cur.append(w)
        if w.get("eos") or w.get("pause", 0) > 1.5:
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)
    txt = [f"[{fmt(l[0]['s'])} #{l[0]['i']}] " + " ".join(x["w"] + ("?" if x["?"] else "") for x in l)
           for l in lines]
    Path(f"{out}.transcript.txt").write_text("\n".join(txt) + "\n")
    print(f"{len(words)} words, {len(lines)} sentences, {len(fillers)} fillers, models agree on {agree:.0%}; "
          f"{total / 60:.1f} min in {time.time() - t0:.0f}s -> {out}.words.json")


if __name__ == "__main__":
    main()
