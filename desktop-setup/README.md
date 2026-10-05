# Desktop-Setup

Skripte und Erweiterungen, mit denen ich den Linux-Desktop (XFCE unter Kali) anpasse.
Die Einstellungen sind umkehrbar: vor jeder Änderung wird der Ursprungszustand gesichert.

## Die Bausteine

| Datei | Was sie tut |
|---|---|
| `bin/terminal-studio` | Oberfläche, um das Terminal (QTerminal) anzupassen: Schrift, Farben, Hintergrund, Cursor. Die Werte werden bei jedem Start des Terminals angewendet. |
| `bin/design-apply` | Ein Befehl für das ganze Farbschema: GTK-Theme, Icons, Fensterrahmen und Qt-Farben. `design-apply Red`, `design-apply zurueck` setzt den Ursprung zurück, `design-apply status` zeigt den aktuellen Stand. |
| `bin/mac-screenshot` | Screenshots im Mac-Stil über Tastenkürzel. Speichert auf dem Schreibtisch und in die Zwischenablage, zeigt danach eine kleine Vorschau. |
| `bin/kuerzel` | Öffnet die Tastenkürzel-Übersicht im Terminal-Studio. |
| `mods/*.py` | Erweiterungen für das Terminal-Studio. Jede Datei ist ein Reiter: Tastenkürzel, Sperre und Energie, Ladebildschirm, Hintergrund, Logo. |

## Was man daran sieht

- **GTK und XFCE:** Einstellungen laufen über `xfconf-query`, also über die offizielle Konfigurationsschnittstelle, nicht durch Dateien von Hand.
- **Python mit GObject:** Fenster mit GTK 3, eigenes CSS, Tastatur- und Mausereignisse.
- **Sicherheit der Änderung:** Vor jeder Änderung wird der alte Zustand in einer Datei gesichert (`*.bak-vor-…`). Ein Rückweg ist damit immer da.
- **Shell-Skripte:** Fallunterscheidungen für Root und den normalen Benutzer, Befehle mit `sudo -u` in der richtigen Sitzung.

## Installation (als Vorlage)

```bash
# Benutzername und Pfade vorher ersetzen (siehe README im Wurzelordner)
sudo install -m 755 bin/* /usr/local/bin/
sudo mkdir -p /usr/local/lib/terminal-studio-mods
sudo cp mods/*.py /usr/local/lib/terminal-studio-mods/
```

Voraussetzungen: Python 3, GTK 3 (`python3-gi`), XFCE mit `xfconf`. Die Skripte erwarten außerdem Hilfsprogramme, die hier nicht enthalten sind (z. B. `aktuelles-display`, `terminal_style_logo_scale`). Das ist ein Hinweis, kein Fehler: Die Skripte sind auf diesen Rechner zugeschnitten.

## Bilder

Bilder vom Terminal-Studio sind bewusst nicht enthalten: Das Programm schreibt in das echte Benutzerprofil, und ein Foto hätte private Teile des Desktops zeigen können.
