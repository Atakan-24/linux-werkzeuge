"""Reiter „Rice“: alles oder einzelne Ebenen des Rice auf den Stand vor dem Rice zurücksetzen.

Arbeitet mit /usr/local/sbin/restore-rice (Sicherungen in ~/rice-backup). Zurücksetzen fragt vorher nach und
braucht das Admin-Passwort (pkexec). Nichts wird gelöscht.
"""
import subprocess, threading
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

TOOL = "/usr/local/sbin/restore-rice"
EBENEN = [("boot", "1 Boot (Ladebildschirm, GRUB)"), ("login", "2 Login-Bildschirm"), ("lock", "3 Sperrbildschirm"),
          ("desktop", "4 Desktop, Leiste, Dock"), ("ui", "5 Fenster, Icons, Mauszeiger"),
          ("terminal", "6 Terminal (Prompt, Banner)"), ("details", "7 Details (Ausschalten, sudo)")]


def _lauf(args, root=False):
    cmd = (["pkexec", TOOL] if root else [TOOL]) + args
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def baue_seite(studio=None):
    g = Gtk.Grid(column_spacing=14, row_spacing=10, margin=14)
    status = Gtk.Label(xalign=0, wrap=True, selectable=True)
    log = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD)
    log.set_size_request(-1, 180)
    zeile = [0]

    def rahmen(w):
        sc = Gtk.ScrolledWindow(); sc.set_min_content_height(180); sc.add(w); return sc

    def aktualisieren(*_a):
        rc, out = _lauf(["status"])
        status.set_text(out if out else "Kein Status.")
        rc, lg = _lauf(["log"])
        log.get_buffer().set_text(lg[-6000:] if lg else "")

    def fragen(text, sek):
        d = Gtk.MessageDialog(transient_for=studio, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text=text)
        d.format_secondary_text(sek)
        a = d.run(); d.destroy()
        return a == Gtk.ResponseType.YES

    def ausfuehren(args, wartet):
        status.set_text(wartet + " (Passwort eingeben) …")
        def arbeit():
            rc, out = _lauf(args, root=True)
            GLib.idle_add(lambda: (aktualisieren(), status.set_text(("Fertig.\n" if rc == 0 else "Hat nicht geklappt.\n") + out[-800:]), False)[2])
        threading.Thread(target=arbeit, daemon=True).start()

    def ebene(_b, key, name):
        if fragen("„%s“ zurücksetzen?" % name, "Diese Ebene geht auf den Stand vor dem Rice zurück. Andere Ebenen bleiben. Nichts wird gelöscht."):
            ausfuehren([key], "Setze %s zurück" % name)

    def alles(_b):
        if fragen("WIRKLICH alles auf den Stand vor dem Rice zurück?", "Alle 7 Ebenen gehen zurück. Nichts wird gelöscht, neue Rice-Dateien werden nur zu „.rice-aus“ umbenannt. Danach bitte neu anmelden."):
            ausfuehren(["all"], "Setze alles zurück")

    def zurueck_rice(_b):
        if fragen("Zurück auf den Rice-Stand?", "Holt den Stand zurück, den du vor dem letzten Zurücksetzen hattest."):
            ausfuehren(["auf-rice"], "Stelle den Rice-Stand wieder her")

    def reihe(label, widget):
        if label:
            g.attach(Gtk.Label(label=label, xalign=0), 0, zeile[0], 1, 1)
        widget.set_hexpand(True); g.attach(widget, 1, zeile[0], 1, 1); zeile[0] += 1

    kopf = Gtk.Label(xalign=0, wrap=True,
                     label="Hier setzt du das Rice zurück – alles auf einmal oder Ebene für Ebene. Die Originale liegen in ~/rice-backup/00-original.")
    kopf.get_style_context().add_class("hint"); g.attach(kopf, 0, zeile[0], 2, 1); zeile[0] += 1
    b_alles = Gtk.Button(label="Alles zurück auf Stand vor dem Rice"); b_alles.get_style_context().add_class("save")
    b_alles.connect("clicked", alles)
    b_rice = Gtk.Button(label="Zurück auf Rice-Stand"); b_rice.connect("clicked", zurueck_rice)
    b_stat = Gtk.Button(label="Status neu laden"); b_stat.connect("clicked", aktualisieren)
    box = Gtk.Box(spacing=8)
    for b in (b_alles, b_rice, b_stat):
        box.pack_start(b, False, False, 0)
    reihe("", box)
    for key, name in EBENEN:
        b = Gtk.Button(label="Zurücksetzen"); b.set_halign(Gtk.Align.START); b.connect("clicked", ebene, key, name)
        reihe(name, b)
    reihe("Status", status)
    reihe("Protokoll", rahmen(log))
    aktualisieren()
    sc = Gtk.ScrolledWindow(); sc.add(g)
    return sc
