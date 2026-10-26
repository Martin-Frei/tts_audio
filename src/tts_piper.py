# src/tts_piper.py


import json
import logging
import wave
from pathlib import Path

from piper import PiperVoice

from stage_io import load_stage, save_stage

logger = logging.getLogger(__name__)


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
        title = title + "."                                 # Wenn title ohne Satzzeichen endet dann ! dazu
    if item.get("teaser"):
        return title + " " + item["teaser"]                 # reutn title + Leerzeichen+ teaser
    return title                                            # ohne teaser nur title zurück


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
        with wave.open(str(wav_path), "wb") as wav_file:                    # Erstellt eine leere WAV Datei
            voice.synthesize_wav(speech_text(item), wav_file)               # Erzeugt die Sprachdatei WAV
        entries.append({"id": item["id"], "wav": str(wav_path)})            # erzuegt die eien Entries mit id udnd en wave_path  ?? müßte hie rnicht wave_file stehen ??        

    save_stage(output_path, run_id, "tts_piper", entries, "ok")             # Speichert die entries mit Status "ok"
    logger.info("tts_piper: %d WAV files written to %s", len(entries), audio_dir)
    return "ok", output_path                                                 # Gibt Status und Ausgabepfad zurück
