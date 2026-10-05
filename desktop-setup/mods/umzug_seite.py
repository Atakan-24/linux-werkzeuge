"""Reiter „Umzug“: alle Einstellungen + Programm in eine Datei packen / auf anderem Rechner einspielen."""
import os, pwd, subprocess, threading, time
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

TOOL = "/usr/local/sbin/terminal-studio-umzug"


def baue_seite(studio):
    g = studio.grid()
    status = Gtk.Label(xalign=0, wrap=True, selectable=True)

    def lauf(cmd, ok_text):
        status.set_text("Einen Moment …")
        def arbeit():
            r = subprocess.run(cmd, capture_output=True, text=True)
            GLib.idle_add(status.set_text, (ok_text + "\n" + r.stdout.strip()) if r.returncode == 0
                          else "Hat nicht geklappt: " + (r.stderr or r.stdout).strip()[-300:])
        threading.Thread(target=arbeit, daemon=True).start()

    def export(_w):
        d = Gtk.FileChooserDialog(title="Umzugsdatei speichern", parent=studio, action=Gtk.FileChooserAction.SAVE)
        d.add_buttons("Abbrechen", Gtk.ResponseType.CANCEL, "Speichern", Gtk.ResponseType.OK)
        ordner = os.path.expanduser("~/Dokumente/Terminal-Studio-Umzug")
        os.makedirs(ordner, exist_ok=True)
        d.set_current_folder(ordner)
        d.set_current_name("terminal-studio-umzug-%s.tar.gz" % time.strftime("%F"))
        d.set_do_overwrite_confirmation(True)
        ok = studio.run_closable_dialog(d, keep_alive=True) == Gtk.ResponseType.OK
        pfad = d.get_filename() if ok else None
        d.destroy()
        if pfad:
            lauf([TOOL, "export", pfad], "Fertig. Diese Datei nimmst du mit:")

    def einspielen(_w):
        d = Gtk.FileChooserDialog(title="Umzugsdatei wählen", parent=studio, action=Gtk.FileChooserAction.OPEN)
        d.add_buttons("Abbrechen", Gtk.ResponseType.CANCEL, "Öffnen", Gtk.ResponseType.OK)
        ok = studio.run_closable_dialog(d, keep_alive=True) == Gtk.ResponseType.OK
        pfad = d.get_filename() if ok else None
        d.destroy()
        if pfad:
            lauf(["pkexec", TOOL, "einspielen", pfad, "--benutzer", pwd.getpwuid(os.getuid()).pw_name,
                  "--ohne-programm"], "Fertig. Terminal-Studio bitte neu öffnen. Vorher wurde alles gesichert.")

    b1 = Gtk.Button(label="Alles in eine Datei packen …"); b1.connect("clicked", export)
    b2 = Gtk.Button(label="Umzugsdatei einspielen …"); b2.connect("clicked", einspielen)
    studio.row(g, "Mitnehmen", b1, "Einstellungen, Profile, Logos, Farben, Kürzel und das Programm selbst")
    studio.row(g, "Einspielen", b2, "Profile und Logos werden zusammengeführt, alles andere ersetzt; vorher Sicherung")
    hinweis = Gtk.Label(label="Auf dem neuen Rechner: Datei entpacken (tar xzf DATEI) und dort  sudo ./installieren.sh  starten.",
                        xalign=0, wrap=True)
    studio.row(g, "Neuer Rechner", hinweis)
    studio.row(g, "", status)
    return g
