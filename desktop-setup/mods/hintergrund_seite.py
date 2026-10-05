"""Reiter „Desktop-Bild“: Desktop-Hintergrundbild wählen (Kali-Bilder, Roter Code, eigenes Bild) und zurücksetzen.

Gesetzt wird über xfconf (Kanal xfce4-desktop, alle „…/last-image“-Eigenschaften), wirkt sofort.
Standard = Roter Code mit Kali-Logo. „Ursprünglich“ = die Bilder, die vor dem Roten Design eingestellt waren
(Sicherung in /usr/share/backgrounds/redcode/alte-hintergruende.txt).
"""
import glob, os
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gtk

from sperre_seite import _xfconf

REDDIR = "/usr/share/backgrounds/redcode"
STANDARD_BILD = f"{REDDIR}/redcode-desktop.png"
ROT_OHNE_LOGO = f"{REDDIR}/redcode-nologo.png"
KALI_DIR = "/usr/share/backgrounds/kali"
ALTE = f"{REDDIR}/alte-hintergruende.txt"
STANDARD_STIL = 5          # 5 = Zoomen (füllt alles)
STILE = [(5, "Zoomen (füllt alles)"), (4, "Einpassen"), (3, "Strecken"), (1, "Mittig"), (2, "Kacheln")]


def _props(ende):
    out = _xfconf(["-c", "xfce4-desktop", "-l"]) or ""
    return [p for p in out.splitlines() if p.endswith(ende)]


def aktuelles_bild():
    for p in _props("/last-image"):
        v = _xfconf(["-c", "xfce4-desktop", "-p", p])
        if v:
            return v
    return STANDARD_BILD


def bild_setzen(pfad, stil=None):
    """Setzt das Bild auf allen Bildschirmen/Arbeitsflächen. True, wenn mindestens ein Eintrag gesetzt wurde."""
    ok = False
    for p in _props("/last-image"):
        ok = _xfconf(["-c", "xfce4-desktop", "-p", p, "-s", pfad]) is not None or ok
    if stil is not None:
        for p in _props("/image-style"):
            _xfconf(["-c", "xfce4-desktop", "-p", p, "-s", str(stil)])
    return ok


def alte_werte():
    """Vor dem Roten Design gesicherte last-image-Werte: {Eigenschaft: Pfad}."""
    out = {}
    try:
        with open(ALTE) as f:
            for zeile in f:
                if "=" in zeile:
                    k, v = zeile.strip().split("=", 1)
                    if k.endswith("/last-image") and os.path.exists(v):
                        out[k] = v
    except OSError:
        pass
    return out


def bilder_liste():
    eintraege = [(STANDARD_BILD, "Roter Code mit Kali-Logo (Standard)"), (ROT_OHNE_LOGO, "Roter Code ohne Logo")]
    for f in sorted(glob.glob(f"{KALI_DIR}/*")):
        if f.lower().endswith((".jpg", ".jpeg", ".png")) and os.path.isfile(f):
            eintraege.append((f, "Kali: " + os.path.basename(f)))
    return eintraege


def baue_seite(studio=None):
    g = Gtk.Grid(column_spacing=14, row_spacing=10, margin=14)
    status = Gtk.Label(xalign=0, wrap=True)
    vorschau = Gtk.Image(); vorschau.set_size_request(460, 259)
    hat_stack = studio is not None and hasattr(studio, "preview_stack")
    if hat_stack:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.pack_start(vorschau, False, False, 0)
        studio.preview_stack.add_named(vbox, "wall")
        vbox.show_all()
    zustand = {"pfad": aktuelles_bild(), "bauen": True}

    def zeige(pfad):
        try:
            vorschau.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(pfad, 460, 259, True))
        except Exception:
            vorschau.clear()

    liste = bilder_liste()
    bild_cb = Gtk.ComboBoxText()
    for pfad, name in liste:
        bild_cb.append(pfad, name)
    bild_cb.append("__datei__", "Eigenes Bild vom PC wählen …")
    if zustand["pfad"] not in [p for p, _ in liste]:
        bild_cb.append(zustand["pfad"], "Aktuell: " + os.path.basename(zustand["pfad"]))
    bild_cb.set_active_id(zustand["pfad"])

    stil_cb = Gtk.ComboBoxText()
    for wert, name in STILE:
        stil_cb.append(str(wert), name)
    aktueller_stil = None
    for p in _props("/image-style"):
        aktueller_stil = _xfconf(["-c", "xfce4-desktop", "-p", p])
        if aktueller_stil:
            break
    stil_cb.set_active_id(aktueller_stil if aktueller_stil in [str(w) for w, _ in STILE] else str(STANDARD_STIL))

    def anwenden(pfad):
        if bild_setzen(pfad, int(stil_cb.get_active_id() or STANDARD_STIL)):
            zustand["pfad"] = pfad
            zeige(pfad)
            status.set_text("Gesetzt: " + os.path.basename(pfad))
        else:
            status.set_text("Hat nicht geklappt – Desktop-Bild konnte nicht gesetzt werden.")

    def bild_geaendert(cb):
        if zustand["bauen"]:
            return
        wahl = cb.get_active_id()
        if wahl == "__datei__":
            d = Gtk.FileChooserDialog(title="Bild wählen", parent=studio, action=Gtk.FileChooserAction.OPEN)
            d.add_buttons("Abbrechen", Gtk.ResponseType.CANCEL, "Öffnen", Gtk.ResponseType.OK)
            f = Gtk.FileFilter(); f.set_name("Bilder"); f.add_mime_type("image/*"); d.add_filter(f)
            gewaehlt = d.get_filename() if d.run() == Gtk.ResponseType.OK else None
            d.destroy()
            zustand["bauen"] = True
            if gewaehlt:
                cb.append(gewaehlt, os.path.basename(gewaehlt)); cb.set_active_id(gewaehlt)
            else:
                cb.set_active_id(zustand["pfad"])
            zustand["bauen"] = False
            if gewaehlt:
                anwenden(gewaehlt)
            return
        if wahl:
            anwenden(wahl)

    def stil_geaendert(_cb):
        if not zustand["bauen"]:
            anwenden(zustand["pfad"])

    def standard(_b=None):
        zustand["bauen"] = True
        bild_cb.set_active_id(STANDARD_BILD); stil_cb.set_active_id(str(STANDARD_STIL))
        zustand["bauen"] = False
        anwenden(STANDARD_BILD)

    def urspruenglich(_b):
        alt = alte_werte()
        if not alt:
            status.set_text("Keine Sicherung der ursprünglichen Bilder gefunden.")
            return
        ok = False
        for prop, pfad in alt.items():
            ok = _xfconf(["-c", "xfce4-desktop", "-p", prop, "-s", pfad]) is not None or ok
        status.set_text("Ursprüngliche Kali-Bilder zurückgesetzt." if ok else "Hat nicht geklappt.")
        if ok:
            zeige(next(iter(alt.values())))

    bild_cb.connect("changed", bild_geaendert)
    stil_cb.connect("changed", stil_geaendert)
    zustand["bauen"] = False
    zeige(zustand["pfad"])

    zeile = [0]

    def reihe(label, widget, hint=None):
        if label:
            g.attach(Gtk.Label(label=label, xalign=0), 0, zeile[0], 1, 1)
        widget.set_hexpand(True); g.attach(widget, 1, zeile[0], 1, 1); zeile[0] += 1
        if hint:
            h = Gtk.Label(label=hint, xalign=0, wrap=True); h.get_style_context().add_class("hint")
            g.attach(h, 1, zeile[0], 1, 1); zeile[0] += 1

    reihe("Desktop-Hintergrund", bild_cb, "Wirkt sofort auf dem Desktop, kein Speichern nötig.")
    reihe("Bild-Anpassung", stil_cb)
    b_std = Gtk.Button(label="Standard (Roter Code)"); b_std.connect("clicked", standard)
    b_alt = Gtk.Button(label="Ursprünglich (Kali wie vorher)"); b_alt.connect("clicked", urspruenglich)
    box = Gtk.Box(spacing=8); box.pack_start(b_std, False, False, 0); box.pack_start(b_alt, False, False, 0)
    reihe("", box)
    reihe("", status)
    if not hat_stack:
        reihe("Vorschau", vorschau)
    else:
        h = Gtk.Label(label="Die Vorschau siehst du rechts.", xalign=0); h.get_style_context().add_class("hint")
        reihe("", h)
    if studio is not None:
        studio.wall_standard = standard
    sc = Gtk.ScrolledWindow(); sc.add(g)
    return sc
