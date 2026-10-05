"""Logo-Verlauf (2-8 Farben), Regenbogen zurücksetzen, Fenster-Schalter."""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def verlauf_farbe(farben, i, n):
    """Farbe (#rrggbb) für Zeile i von n bei linearem Verlauf durch farben."""
    if len(farben) == 1 or n < 2:
        return farben[0]
    t = i / (n - 1) * (len(farben) - 1)
    k = min(int(t), len(farben) - 2)
    f = t - k
    a = [int(farben[k][j:j + 2], 16) for j in (1, 3, 5)]
    b = [int(farben[k + 1][j:j + 2], 16) for j in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * f + .5) for x, y in zip(a, b))


def farben_lesen(b):
    v = b.get("LOGO_FARBEN", "")
    return [x for x in v.split(",") if len(x) == 7 and x[0] == "#"] if v else []


def baue_zeilen(studio, g):
    """Fügt Verlaufs-Zeile, Regenbogen-Knopf und Fenster-Schalter in die Banner-Seite ein."""
    box = Gtk.Box(spacing=6)
    knoepfe = Gtk.Box(spacing=4)
    box.pack_start(knoepfe, False, False, 0)

    def neu_zeichnen():
        for c in knoepfe.get_children():
            knoepfe.remove(c)
        for idx, farbe in enumerate(farben_lesen(studio.b)):
            kb = Gtk.ColorButton(rgba=studio.rgba(farbe))
            kb.connect("color-set", waehlen, idx)
            knoepfe.pack_start(kb, False, False, 0)
        knoepfe.show_all()

    def speichern(liste):
        studio.b["LOGO_FARBEN"] = ",".join(liste)
        if liste:
            studio.b["REGENBOGEN"] = "nein"
            try:
                studio.rainbow_switch.set_active(False)
            except Exception:
                pass
        studio.update_banner_preview()
        neu_zeichnen()

    def waehlen(btn, idx):
        r = btn.get_rgba()
        liste = farben_lesen(studio.b)
        liste[idx] = "#%02x%02x%02x" % (int(r.red * 255), int(r.green * 255), int(r.blue * 255))
        speichern(liste)

    def plus(_w):
        liste = farben_lesen(studio.b)
        if not liste:
            liste = [studio.b.get("LOGO_COLOR", "#f2d6d6")]
        if len(liste) < 8:
            liste.append("#ff5555" if len(liste) == 1 else liste[-1])
        speichern(liste)

    def minus(_w):
        speichern(farben_lesen(studio.b)[:-1])

    def regenbogen(_w):
        studio.b["LOGO_FARBEN"] = ""
        studio.b["REGENBOGEN"] = "ja"
        try:
            studio.rainbow_switch.set_active(True)
        except Exception:
            pass
        studio.update_banner_preview()
        neu_zeichnen()

    for text, fn in (("＋", plus), ("−", minus), ("Regenbogen wiederherstellen", regenbogen)):
        bt = Gtk.Button(label=text)
        bt.connect("clicked", fn)
        box.pack_start(bt, False, False, 0)
    neu_zeichnen()
    studio.row(g, "Logo-Verlauf (2–8 Farben)", box,
               "Mehrere Farben von oben nach unten; „＋“ fügt eine hinzu")
    sw = Gtk.Switch(halign=Gtk.Align.START)
    sw.set_active(studio.b.get("LOGO_FENSTER_AUFWEITEN") == "ja")
    sw.connect("notify::active", lambda w, _p: studio.b.__setitem__(
        "LOGO_FENSTER_AUFWEITEN", "ja" if w.get_active() else "nein"))
    studio.row(g, "Fenster für großes Logo breiter machen", sw,
               "Aus: Logo wird am Rand abgeschnitten, das Fenster bleibt so groß wie es ist")
