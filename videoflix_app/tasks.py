import subprocess
import shlex
import os

def convert_480p(source):
    # Zerlege den Pfad in den Teil vor der Erweiterung (root) und die Erweiterung (ext)
    # Beispiel: source = "/app/media/videos/Haloween.mp4"
    # root wird zu: "/app/media/videos/Haloween"
    # ext wird zu:  ".mp4"
    root, ext = os.path.splitext(source)
    
    # Baue den neuen Ziel-Dateinamen korrekt zusammen
    # Ergebnis: "/app/media/videos/Haloween_480p.mp4"
    target = f"{root}_480p{ext}"
    
    # Der Befehl als String, jetzt mit dem korrekten `target`-Pfad
    # (f-string wird hier für bessere Lesbarkeit verwendet)
    cmd_string = f'ffmpeg -i "{source}" -s hd480 -c:v libx264 -crf 23 -c:a aac -strict -2 "{target}"'
    
    # Den String sicher in eine Liste von Argumenten aufteilen
    cmd_list = shlex.split(cmd_string)
    
    try:
        print(f"Starte Konvertierung: {source} -> {target}")
        subprocess.run(cmd_list, check=True)
        print("Konvertierung erfolgreich abgeschlossen.")
    except FileNotFoundError:
        print("FEHLER: 'ffmpeg' wurde nicht gefunden. Ist es im System-PATH installiert?")
    except subprocess.CalledProcessError as e:
        print(f"Ein Fehler ist während der Videokonvertierung aufgetreten: {e}")
    