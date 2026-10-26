# src/postprocess.py


"""Stage postprocess: join all WAVs with a gong, set loudness, write one MP3.

Reads the _tts_piper.json (list of WAVs in broadcast order) and writes
one MP3 for the whole briefing, plus the _postprocess.json with its path.
The order comes from the list, not from the folder: the folder is sorted
by id, the list by broadcast order.

The gong is generated with ffmpeg (two soft tones, chosen 2026-10-26),
so no recording and no licence is needed. It belongs here and not in
tts_piper, so tts_gemini in Phase 3 gets the same gong without new code.

Workflow (postprocess):
    1. Receive input_path, output_path and run_id from run.py.
    2. Load the WAV list with load_stage().
       If it cannot be read or is empty: status "abort" with a reason.
    3. Generate the gong once with make_gong(), in the format of the
       Piper WAVs (22050 Hz, mono), with a short silence before and after.
    4. Write the concat list with concat_lines(): item, gong, item, gong,
       ..., item. No gong after the last item.
    5. Run ffmpeg once: join everything, set the loudness of the whole
       briefing to -16 LUFS (loudnorm), write the MP3.
       If ffmpeg is missing or fails: status "abort" with a reason.
    6. Write the _postprocess.json with save_stage(), status "ok".
    7. Return (status, output_path) to run.py.

Functions:
    concat_lines(wav_paths, gong_path)    lines for the ffmpeg concat list
    make_gong(gong_path)                  generate the gong WAV with ffmpeg
    postprocess(input_path, output_path, run_id)
                                          run the stage, return (status, path)

Dependencies:
    ffmpeg (program, not a Python package, installed with winget),
    stage_io (own module), standard library: json, logging, subprocess, pathlib.

Start and test:
    python -m pytest -v
"""

import json
import logging
import subprocess
from pathlib import Path

from stage_io import load_stage, save_stage

logger = logging.getLogger(__name__)

# Target loudness for podcasts. LUFS measures loudness as the ear hears it.
TARGET_LUFS = -16                               # Ziel Lautstärke für mp3

# Two soft tones, high to lower (variant A, chosen by ear on 2026-10-26),
# 0.3 s silence before and after, so the gong does not stick to the voice.
GONG_FILTER = (
    "[0][1]concat=n=2:v=0:a=1,"                                 # Verbindet die beiden separaten Sinus-Tonspuren (Audiostöße) hintereinander
    "afade=t=in:d=0.02,afade=t=out:st=0.3:d=0.1,volume=0.3,"    # Blendet ein/aus, passt die Lautstärke auf 30% an
    "adelay=300,apad=pad_dur=0.3"                               # Fügt 300ms Verzögerung am Anfang und Stille (Padding) am Ende hinzu
)


def concat_lines(wav_paths, gong_path):
    """Return the lines of the ffmpeg concat list: item, gong, item, ... item.

    >>> concat_lines(["a.wav", "b.wav", "c.wav"], "gong.wav")
    ["file 'a.wav'", "file 'gong.wav'", "file 'b.wav'", "file 'gong.wav'", "file 'c.wav'"]
    >>> concat_lines(["a.wav"], "gong.wav")
    ["file 'a.wav'"]
    """
    lines = []
    for number, wav in enumerate(wav_paths):
        # A gong between two items, not before the first and not after the last.
        if number > 0:                                  
            lines.append(f"file '{gong_path}'")         # Fügt vor jedem weiteren Artikel (außer dem ersten) den Gong-Trennpfad ein
        lines.append(f"file '{wav}'")                   # Fügt den Dateipfad des jeweiligen Audio-Beitrags hinzu
    return lines                                        # Gibt die vollständige Liste der Concat-Einträge zurück


def make_gong(gong_path):
    """Generate the gong WAV with ffmpeg, in the format of the Piper WAVs."""
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error",                      # Startet FFmpeg im stillen Modus, überschreibt bestehende Dateien (-y)
         "-f", "lavfi", "-i", "sine=frequency=880:duration=0.15",   # Erzeugt den ersten Ton (hoher Sinus, 880 Hz, 0.15s)
         "-f", "lavfi", "-i", "sine=frequency=660:duration=0.25",   # Erzeugt den zweiten Ton (tieferer Sinus, 660 Hz, 0.25s)
         "-filter_complex", GONG_FILTER,                            # Wendet den definierten Audio-Filter-Komplex (Fade, Delay, Lautstärke) an
         "-ar", "22050", "-ac", "1", str(gong_path)],               # Setzt Abtastrate auf 22.05 kHz, Mono (-ac 1) und speichert als WAV
        check=True,                                                 # Löst bei Fehlern eine Exception aus
    )


def postprocess(input_path, output_path, run_id):
    """Run the stage postprocess and report (status, output_path) to run.py."""
    try:
        data = load_stage(input_path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        reason = f"input not readable: {error}"
        save_stage(output_path, run_id, "postprocess", [], "abort", reason)
        return "abort", output_path

    if not data["items"]:
        reason = "no WAV files in input"
        save_stage(output_path, run_id, "postprocess", [], "abort", reason)
        return "abort", output_path

    output_path = Path(output_path)
    run_dir = output_path.parent
    # news_2026-10-26_0800_postprocess.json -> news_2026-10-26_0800.mp3
    mp3_path = run_dir / (output_path.stem.removesuffix("_postprocess") + ".mp3")   # Leitet den finalen MP3-Pfad vom JSON-Dateinamen ab
    gong_path = run_dir / "audio" / "gong.wav"                                      # Legt den Pfad für die generierte Gong-Datei fest
    list_path = run_dir / "audio" / "concat.txt"                                    # Legt den Pfad für die FFmpeg-Text-Concat-Liste fest
    
    # ffmpeg reads paths in the list with forward slashes on every system.
    wav_paths = [Path(entry["wav"]).resolve().as_posix() for entry in data["items"]]

    try:
        make_gong(gong_path)                                                        # Generiert die Gong-Audiodatei via FFmpeg
        lines = concat_lines(wav_paths, gong_path.resolve().as_posix())             # Erstellt die Dateiliste inklusive Gongs zwischen den Artikeln
        list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")             # Schreibt die Concat-Liste in eine Textdatei
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",                                  # Startet FFmpeg zum Zusammenfügen, Normalisieren und Kodieren
             "-f", "concat", "-safe", "0", "-i", str(list_path),                    # Nutzt das Concat-Demuxer-Format mit der erstellten Textliste
             "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11",                     # Normalisiert die Lautstärke auf das Ziel-LUFS (EBU R128)
             "-ar", "44100", "-ac", "1",                                            # Setzt Abtastrate auf 44.1 kHz und Mono-Modus
             "-codec:a", "libmp3lame", "-b:a", "96k", str(mp3_path)],               # Kodiert als MP3 (libmp3lame) mit 96 kbps Bitrate
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        # FileNotFoundError: ffmpeg is not installed or not on the PATH.
        # CalledProcessError: ffmpeg ran but failed.
        reason = f"ffmpeg failed: {error}"
        save_stage(output_path, run_id, "postprocess", [], "abort", reason)
        return "abort", output_path

    save_stage(output_path, run_id, "postprocess", [{"mp3": str(mp3_path)}], "ok")
    logger.info("postprocess: %d items joined into %s", len(wav_paths), mp3_path)
    return "ok", output_path
