"""Text-Logo als Hintergrundbild in der Mitte (wird als PNG gerendert)."""
import colorsys, json, os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from PIL import Image, ImageDraw, ImageFont

DIR = os.path.expanduser("~/.config/terminal-style")
PNG = os.path.join(DIR, "logo-hintergrund.png")
CFG = os.path.join(DIR, "logo-hintergrund.json")
BASEN = {"schwarz": "Schwarz", "roter-code": "Roter Code ohne Logo", "farbschema": "Dunkelgrau"}
REDBG_NOLOGO = "/usr/share/backgrounds/redcode/redcode-nologo.png"
SCHRIFTEN = ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
             "/usr/share/fonts/truetype/firacode/FiraCode-Regular.ttf")
STANDARD = {"logo": "arch", "groesse": 60, "deckkraft": 90, "basis": "roter-code", "farbe": "regenbogen",
            "farben": "#ff5555,#5555ff"}


def _hex(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def zeilenfarbe(cfg, i, n):
    if cfg["farbe"] == "regenbogen":
        r, g, b = colorsys.hsv_to_rgb((i / max(n, 1)) % 1.0, 0.75, 1.0)
        return int(r * 255), int(g * 255), int(b * 255)
    fs = [f for f in cfg["farben"].split(",") if len(f) == 7] or ["#f2d6d6"]
    if cfg["farbe"] == "eine" or len(fs) == 1 or n < 2:
        return _hex(fs[0])
    t = i / (n - 1) * (len(fs) - 1)
    k = min(int(t), len(fs) - 2); f = t - k
    return tuple(int(x + (y - x) * f + .5) for x, y in zip(_hex(fs[k]), _hex(fs[k + 1])))


def rendern(art, cfg, ziel=PNG, breite=1920, hoehe=1080):
    if cfg["basis"] == "roter-code" and os.path.exists(REDBG_NOLOGO):
        bild = Image.open(REDBG_NOLOGO).convert("RGB").resize((breite, hoehe))
    else:
        bild = Image.new("RGB", (breite, hoehe), (0, 0, 0) if cfg["basis"] == "schwarz" else (24, 24, 28))
    zeilen = art.rstrip("\n").split("\n")
    if not any(z.strip() for z in zeilen):
        bild.save(ziel); return ziel
    pfad = next((p for p in SCHRIFTEN if os.path.exists(p)), None)
    ziel_h = hoehe * cfg["groesse"] / 100.0
    gr = max(6, int(ziel_h / (len(zeilen) * 1.15)))
    while True:
        f = ImageFont.truetype(pfad, gr) if pfad else ImageFont.load_default()
        zh = int(gr * 1.15)
        br = max(int(f.getlength(z)) for z in zeilen)
        if (br <= breite * 0.95 and zh * len(zeilen) <= hoehe * 0.95) or gr <= 6:
            break
        gr -= 1
    ebene = Image.new("RGBA", (breite, hoehe), (0, 0, 0, 0))
    d = ImageDraw.Draw(ebene)
    y0 = (hoehe - zh * len(zeilen)) // 2
    alpha = int(255 * cfg["deckkraft"] / 100)
    for i, z in enumerate(zeilen):
        x0 = (breite - br) // 2
        d.text((x0, y0 + i * zh), z, font=f, fill=zeilenfarbe(cfg, i, len(zeilen)) + (alpha,))
    bild = Image.alpha_composite(bild.convert("RGBA"), ebene).convert("RGB")
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    bild.save(ziel)
    return ziel


def laden():
    try:
        with open(CFG) as f:
            return {**STANDARD, **json.load(f)}
    except Exception:
        return dict(STANDARD)


def dialog(studio, wahl, art_von):
    """wahl: [(key, Name)]; art_von(key)->Text. Gibt Pfad des PNG oder None zurück."""
    cfg = laden()
    d = Gtk.Dialog(title="Text-Logo in der Mitte", transient_for=studio, modal=True)
    d.add_buttons("Abbrechen", Gtk.ResponseType.CANCEL, "Übernehmen", Gtk.ResponseType.OK)
    g = Gtk.Grid(row_spacing=8, column_spacing=10, margin=14)
    d.get_content_area().add(g)
    logo = Gtk.ComboBoxText()
    for k, n in wahl:
        if k != "aus":
            logo.append(k, n)
    logo.set_active_id(cfg["logo"]) if cfg["logo"] in [k for k, _ in wahl] else logo.set_active(0)
    basis = Gtk.ComboBoxText()
    for k, n in BASEN.items():
        basis.append(k, n)
    basis.set_active_id(cfg["basis"])
    farbe = Gtk.ComboBoxText()
    for k, n in (("regenbogen", "Regenbogen"), ("eine", "Eine Farbe"), ("verlauf", "Eigener Verlauf (2 Farben)")):
        farbe.append(k, n)
    farbe.set_active_id(cfg["farbe"])
    fs = (cfg["farben"].split(",") + ["#ff5555", "#5555ff"])[:2]
    k1 = Gtk.ColorButton(); k2 = Gtk.ColorButton()
    from gi.repository import Gdk
    for kb, h in ((k1, fs[0]), (k2, fs[1])):
        c = Gdk.RGBA(); c.parse(h); kb.set_rgba(c)
    gs = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 20, 100, 1); gs.set_value(cfg["groesse"])
    dk = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 100, 1); dk.set_value(cfg["deckkraft"])
    gs._standard = STANDARD["groesse"]; dk._standard = STANDARD["deckkraft"]
    for z, (t, w) in enumerate((("Logo", logo), ("Größe (%)", gs), ("Deckkraft (%)", dk), ("Untergrund", basis),
                                ("Farbart", farbe), ("Farbe 1 / Farbe 2", None))):
        g.attach(Gtk.Label(label=t, xalign=0), 0, z, 1, 1)
        if w is None:
            b = Gtk.Box(spacing=6); b.add(k1); b.add(k2); w = b
        w = studio.mit_standard(w) if hasattr(studio, "mit_standard") else w
        w.set_hexpand(True); w.set_size_request(260, -1); g.attach(w, 1, z, 1, 1)
    d.show_all()
    ok = studio.run_closable_dialog(d, keep_alive=True) == Gtk.ResponseType.OK
    if ok:
        def hx(kb):
            r = kb.get_rgba(); return "#%02x%02x%02x" % (int(r.red * 255), int(r.green * 255), int(r.blue * 255))
        cfg.update(logo=logo.get_active_id(), groesse=int(gs.get_value()), deckkraft=int(dk.get_value()),
                   basis=basis.get_active_id(), farbe=farbe.get_active_id(), farben=hx(k1) + "," + hx(k2))
    d.destroy()
    if not ok:
        return None
    os.makedirs(DIR, exist_ok=True)
    with open(CFG, "w") as f:
        json.dump(cfg, f)
    rendern(art_von(cfg["logo"]), cfg)
    os.chmod(PNG, 0o644)
    return PNG
