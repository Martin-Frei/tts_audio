# src/tts_piper.py


"""Stage tts_piper: turn every selected item into speech, one WAV per item.

Reads the _select_items.json and writes one WAV per item into the
subfolder audio/ of the run folder, plus the _tts_piper.json with the
list of WAV files in broadcast order. postprocess reads this list, not
the folder, because the folder is sorted by id, not by broadcast order.

tts_piper only turns text into speech. The gong between items, the
loudness and the MP3 are the job of postprocess, so tts_gemini in
Phase 3 gets them without building them again.

Workflow (tts_piper):
    1. Receive input_path, output_path, run_id and voice_path from run.py.
    2. Load the input file with load_stage() and the voice with
       PiperVoice.load(), once for all items.
       If one of them cannot be read: status "abort" with a reason.
    3. If the input has no items: status "abort" with a reason.
    4. For each item: join title and teaser with speech_text() and write
       the WAV with write_speech(), which adds a pause between sentences.
    5. Write the list (id and WAV path per item) with save_stage(),
       status "ok".
    6. Return (status, output_path) to run.py.

Functions:
    speech_text(item)                         title and teaser as one text
    write_speech(voice, text, wav_path, pause=SENTENCE_PAUSE)
                                              one WAV, pause between sentences
    tts_piper(input_path, output_path, run_id, voice_path)
                                              run the stage, return (status, path)

Dependencies:
    piper-tts (PiperVoice), stage_io (own module),
    standard library: json, logging, wave, pathlib.
    The voice files (.onnx and .onnx.json) are not a Python package:
    they lie in voices/, which is not in the repository.

Start and test:
    python -m pytest -v
"""

import json
import logging
import wave
from pathlib import Path

from piper import PiperVoice

from stage_io import load_stage, save_stage

logger = logging.getLogger(__name__)

SENTENCE_PAUSE = 0.4   # seconds of silence between two sentences


def speech_text(item):
    """Join title and teaser into one text for speech.

    The title gets a full stop, so Piper pauses before the teaser.

    >>> speech_text({"title": "Brand in Beispielstadt", "teaser": "Die Feuerwehr ist vor Ort."})
    'Brand in Beispielstadt. Die Feuerwehr ist vor Ort.'
    >>> speech_text({"title": "Wann kommt die Reform?", "teaser": None})
    'Wann kommt die Reform?'
    """
    title = item["title"]
    if not title.endswith((".", "!", "?")):
        title = title + "."                                 # Wenn title ohne Satzzeichen endet dann .
    if item.get("teaser"):
        return title + " " + item["teaser"]                 # reutn title + Leerzeichen+ teaser
    return title                                            # ohne teaser nur title zurück


def write_speech(voice, text, wav_path, pause=SENTENCE_PAUSE):
    """Write one WAV file, with a pause between the sentences."""
    with wave.open(str(wav_path), "wb") as wav_file:
        first = True
        for chunk in voice.synthesize(text):
            if first:
                # The format comes from the voice: sample rate, bytes per value, channels.
                wav_file.setframerate(chunk.sample_rate)
                wav_file.setsampwidth(chunk.sample_width)
                wav_file.setnchannels(chunk.sample_channels)
                first = False
            else:
                # Silence is zeros: values per second x seconds x bytes per value.
                frames = int(chunk.sample_rate * pause)
                wav_file.writeframes(bytes(frames * chunk.sample_width * chunk.sample_channels))
            wav_file.writeframes(chunk.audio_int16_bytes)


def tts_piper(input_path, output_path, run_id, voice_path):
    """Run the stage tts_piper: one WAV per item, list of files to run.py."""
    try:
        data = load_stage(input_path)                                       # Lädt Daten von inputh pfad
        voice = PiperVoice.load(str(voice_path))                            # Lädt Piper Modell
    except (FileNotFoundError, json.JSONDecodeError) as error:
        reason = f"input or voice not readable: {error}"                    # Erstellt eine Fehlermeldung (Lesefehler, JASON)
        save_stage(output_path, run_id, "tts_piper", [], "abort", reason)   # Speichert Status mit Abbruchgrund
        return "abort", output_path                                         # Gibt Status abort und Pfad zurück

    if not data["items"]:
        reason = "no items in input"                                        # Erstellt eine Fehlermeldung (keine Artikel)
        save_stage(output_path, run_id, "tts_piper", [], "abort", reason)   # Speichert Status mit Abbruchgrund 
        return "abort", output_path                                         # Gibt Status und Ausgabepfad zurück

    audio_dir = Path(output_path).parent / "audio"                          # Zieordner für WAV Dateien
    audio_dir.mkdir(parents=True, exist_ok=True)                            # Erstellt Ordner falls nicht da 

    entries = []                                                            # Erzeugt leere Liste
    for item in data["items"]:                                              # Iteriert durch alle items in data
        wav_path = audio_dir / f"{item['id']}.wav"                          # Erzeugt eien eindeutigen Dateinamen mit der id 
        write_speech(voice, speech_text(item), wav_path)                    # Erzeugt die Sprachdatei WAV, mit Pause zwischen den Sätzen
        entries.append({"id": item["id"], "wav": str(wav_path)})            # erzuegt die eie Entries mit id und den wave_path         

    save_stage(output_path, run_id, "tts_piper", entries, "ok")             # Speichert die entries mit Status "ok"
    logger.info("tts_piper: %d WAV files written to %s", len(entries), audio_dir)
    return "ok", output_path                                                 # Gibt Status und Ausgabepfad zurück
