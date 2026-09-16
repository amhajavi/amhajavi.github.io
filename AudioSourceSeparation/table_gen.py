#!/usr/bin/env python3
"""
Build a demo page showing audios and videos
Usage:
    python html_gen.py --data data_dir --out table.html
"""
import base64
import mimetypes
import html
import shutil
import argparse
from dataclasses import dataclass, field
from pathlib import Path

VIDEO_EXTS = {".mp4", ".webm", ".mov"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg"}

VIDEO_MIME = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"}
AUDIO_MIME = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".flac": "audio/flac",
              ".m4a": "audio/mp4", ".aac": "audio/aac", ".ogg": "audio/ogg"}


@dataclass
class ModalityTable:
    modality: str                      # "audios" xor "videos"
    models: list[str]                  # column headers, sorted
    n_rows: int                        # n = min samples across models
    cells: list[list[Path | None]]     # cells[model_idx][row]
    static_prefix: str                 # e.g. "media/videos"


def scan_modality(root: Path, modality: str, exts: set[str]) -> ModalityTable:
    """Scan root/modality/models/vids and build the n x d table."""
    modality_dir = root / modality
    model_dirs = sorted(d for d in modality_dir.iterdir() if d.is_dir())

    per_model: list[list[Path]] = []
    for md in model_dirs:
        files = sorted(p for p in md.iterdir() if p.suffix.lower() in exts)
        per_model.append(files)

    n = min((len(f) for f in per_model), default=0)
    cells = [[fs[i] if i < len(fs) else None for fs in per_model] for i in range(n)]
    # transposed below in to_table; store as-is per model
    return ModalityTable(
        modality=modality,
        models=[md.name for md in model_dirs],
        n_rows=n,
        cells=cells,          # cells[row][model_idx]
        static_prefix=f"{root}/{modality}",
    )

def data_uri(f: Path, mime: str) -> str:
    payload = base64.b64encode(f.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def render_table(t: ModalityTable, embed: bool) -> str:
    label = "Audios" if t.modality == "audios" else "Videos"

    tag, mime_map = (("audio", AUDIO_MIME) if t.modality=="audios"
                     else ("video", VIDEO_MIME))

    head = "".join(f"<th class='model'>{html.escape(m)}</th>" for m in t.models)
    rows_html = [f"<tr><th class='model'>Sample</th>{head}</tr>"]

    for r in range(t.n_rows):
        cells = [f"<td class='idx'>#{r + 1}</td>"]
        for m_idx in range(len(t.models)):
            f = t.cells[r][m_idx]
            if f is None:                       # unreachable when n = min, kept for safety
                cells.append("<td>—</td>")
                continue
            rel = f"{t.static_prefix}/{t.models[m_idx]}/{f.name}"
            rel = html.escape(rel, quote=True)
            mime = html.escape(mime_map.get(f.suffix.lower(), "application/octet-stream"), quote=True)

            if embed: # embed the media as base64 in the HTML
                uri = data_uri(f, mime)
                cells.append(f"<td><{tag} controls preload='metadata'>"
                             f"<source src='{uri}' type='{mime}'>"
                             f"Unsupported {tag}.</{tag}></td>")
            else: # without embedding, just link to the file 
                cells.append(f"<td><{tag} controls preload='metadata'>"
                            f"<source src='{rel}' type='{mime}'>"
                            f"Unsupported {tag}.</{tag}></td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    caption = f"{label} ({t.n_rows} samples × {len(t.models)} models)"
    return (f"<h2 class='section'>{html.escape(caption)}</h2>"
            f"<table>{''.join(rows_html)}</table>")


def main():

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    
    ap.add_argument("--root", type=Path, required=True,
                    help="Root dir containing videos/ and/or audios/")
    ap.add_argument("--out", type=Path, default=Path("project.html"))


    ap.add_argument("--embed", action="store_true", help="Embed media as base64 in HTML (slower, larger file)")
    ap.add_argument("--templates", default=None, help="dir containing custom templates")
    ap.add_argument("--title", default="Audio Source Separation Demo")
    ap.add_argument("--subtitle", default="Audio AI Team · Noah's Ark Lab · Huawei Technologies")
    ap.add_argument("--footer", default="Noah's Ark Lab, Huawei Technologies, 2026")
    args = ap.parse_args()

    modalities = [
        ("audios", AUDIO_EXTS),
        ("videos", VIDEO_EXTS),
    ]

    page_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head></head>
    <body>
        {tables}
    </body>
    </html>
    """

    tables: list[ModalityTable] = []
    for name, exts in modalities:
        if not (args.root / name).is_dir():
            print(f"[skip] '{name}/' not present")
            continue
        t = scan_modality(args.root, name, exts)
        if t.n_rows == 0:
            print(f"[skip] '{name}': n = 0 (no samples)")
            continue
        tables.append(t)
        print(f"[ok]   '{name}': d={len(t.models)} models, n={t.n_rows} rows")

    if not tables:
        raise SystemExit("Nothing to render: no modality had n > 0.")

    sections = "\n".join(render_table(t, args.embed) for t in tables)

    page = page_template.format(
        tables=sections,
        footer=args.footer
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()