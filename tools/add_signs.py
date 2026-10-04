#!/usr/bin/env python3
"""Add sign videos and/or studio exports to the shared vocabulary (signs.json).

Usage: python3 tools/add_signs.py FILE [FILE ...]
  - video files (.mp4 .mov .webm .m4v): the file name is the word, e.g. "תודה.mp4".
    Each clip is cropped to 3:4, scaled to 480x640, muted and compressed into videos/.
  - .json files exported from the studio: their motion-data signs are merged in.
A word that already exists keeps its other data (a video and avatar motion can live side by side).
"""
import hashlib, json, pathlib, subprocess, sys, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SIGNS = ROOT / "signs.json"
VIDEOS = ROOT / "videos"
VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}


def norm(word: str) -> str:
    word = unicodedata.normalize("NFC", word).strip()
    return " ".join(word.split())


def load():
    if SIGNS.exists():
        return json.loads(SIGNS.read_text(encoding="utf-8"))
    return {"app": "sign-studio", "version": 1, "signs": []}


def entry_for(data, name):
    for s in data["signs"]:
        if norm(s["name"]) == name:
            return s
    s = {"id": "w" + hashlib.sha1(name.encode()).hexdigest()[:10], "name": name}
    data["signs"].append(s)
    return s


def add_video(data, path: pathlib.Path):
    name = norm(path.stem)
    s = entry_for(data, name)
    VIDEOS.mkdir(exist_ok=True)
    out = VIDEOS / f"{s['id']}.mp4"
    vf = ("crop='min(iw,ih*3/4)':'min(ih,iw*4/3)',scale=480:640:flags=lanczos,"
          "fps=25,format=yuv420p")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-an", "-vf", vf,
                    "-c:v", "libx264", "-profile:v", "main", "-preset", "slow", "-crf", "27",
                    "-movflags", "+faststart", str(out)], check=True)
    s["video"] = f"videos/{out.name}"
    return name, out.stat().st_size


def add_export(data, path: pathlib.Path):
    added = []
    for sign in json.loads(path.read_text(encoding="utf-8")).get("signs", []):
        if sign.get("example") or not sign.get("frames"):
            continue
        s = entry_for(data, norm(sign["name"]))
        s["frames"] = sign["frames"]
        added.append(s["name"])
    return added


def main(files):
    data = load()
    for f in map(pathlib.Path, files):
        if f.suffix.lower() in VIDEO_EXT:
            name, size = add_video(data, f)
            print(f"video  {name}  ({size // 1024} KB)")
        elif f.suffix.lower() == ".json":
            for name in add_export(data, f):
                print(f"motion {name}")
        else:
            print(f"skipped {f.name}: not a video or studio export")
    data["signs"].sort(key=lambda s: s["name"])
    SIGNS.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"signs.json now has {len(data['signs'])} words")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
