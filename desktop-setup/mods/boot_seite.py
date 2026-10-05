"""Reiter „Ladebildschirm“: Vorschau, Modus, Hintergrund (Code/Schwarz/Bild), Logos (eigene Bilder, löschen, Kali),
Text unter dem Logo, Start-Text, eigene Schrift, Farbe/Regenbogen."""
import json, os, re, shutil, subprocess, tempfile, threading
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

CFG = os.path.expanduser("~/.config/terminal-style/boot.json")
BILDER = os.path.expanduser("~/.config/terminal-style/boot-bilder")
STANDARD = {"modus": "redcode", "farbe": "eine", "farbe1": "#ff2828", "dichte": 46, "logo_hoehe": 330,
            "logo_keys": ["kali-original"], "texte": "", "startzeilen": "", "zeilen_farbe": "#ff2828",
            "zeilen_regenbogen": False, "startzeilen_groesse": 16, "hintergrund": "code", "hg_bild": "",
            "hg_dunkel": 55, "unterschrift": "", "unterschrift_font": "slant", "unterschrift_groesse": 14,
            "schrift": "", "dateilogos": [], "verborgen": []}
KALI_LOGOS = [("kali-original", "Kali Drache (Original, glatt)"), ("kali-schriftzug", "Kali Schriftzug")]
FIGLET_FONTS = ("plain", "standard", "slant", "smslant", "small", "mini", "big", "block", "lean", "shadow", "smshadow")
NAME_OK = re.compile(r"[^A-Za-z0-9_.-]")


def laden():
    try:
        with open(CFG) as f:
            return {**STANDARD, **json.load(f)}
    except Exception:
        return dict(STANDARD)


def _generator():
    import importlib.machinery, importlib.util
    l = importlib.machinery.SourceFileLoader("tsb", "/usr/local/sbin/terminal-studio-boot")
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader("tsb", l)); l.exec_module(m)
    return m


def _kopieren(quelle, prefix):
    """Datei in den Bilder-Ordner kopieren; gibt den Namen darin zurück."""
    os.makedirs(BILDER, exist_ok=True)
    name = prefix + NAME_OK.sub("_", os.path.basename(quelle))[-70:]
    shutil.copyfile(quelle, os.path.join(BILDER, name))
    return name


def _datei_waehlen(studio, titel, endungen):
    d = Gtk.FileChooserDialog(title=titel, transient_for=studio, action=Gtk.FileChooserAction.OPEN)
    d.add_buttons("Abbrechen", Gtk.ResponseType.CANCEL, "Öffnen", Gtk.ResponseType.OK)
    f = Gtk.FileFilter(); f.set_name(", ".join(endungen))
    for e in endungen:
        f.add_pattern("*" + e); f.add_pattern("*" + e.upper())
    d.add_filter(f)
    ok = d.run() == Gtk.ResponseType.OK
    pfad = d.get_filename() if ok else None
    d.destroy()
    return pfad


def baue_seite(studio, art_von_studio):
    cfg = laden()
    g = studio.grid()

    def art_von(key):
        if key in ("kali-original", "kali-schriftzug"):
            return "@" + key
        if key.startswith("datei:"):
            return "@" + key
        return art_von_studio(key)

    def abschnitt(text):
        l = Gtk.Label(xalign=0); l.set_markup("<b>%s</b>" % GLib.markup_escape_text(text))
        studio.row(g, "", l)

    # ---------- Vorschau ----------
    vorschau_bild = Gtk.Image(); vorschau_bild.set_size_request(460, 259)
    vorschau_status = Gtk.Label(xalign=0, label="Vorschau: so ungefähr sieht der Ladebildschirm aus.")
    vorschau_status.set_line_wrap(True); vorschau_status.set_max_width_chars(42)
    if hasattr(studio, "preview_stack"):        # Vorschau rechts (statt Terminal-Vorschau), nicht mitten im Reiter
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.pack_start(vorschau_bild, False, False, 0)
        vbox.pack_start(vorschau_status, False, False, 0)
        studio.preview_stack.add_named(vbox, "boot")
        vbox.show_all()
        hinweis = Gtk.Label(xalign=0, label="Die Vorschau siehst du rechts.")
        hinweis.get_style_context().add_class("hint")
        studio.row(g, "", hinweis)
    else:
        studio.row(g, "Vorschau", vorschau_bild)
        studio.row(g, "", vorschau_status)

    # ---------- Modus ----------
    modus = Gtk.ComboBoxText()
    modus.append("redcode", "Eigener Ladebildschirm (mit allem unten)")
    modus.append("kali-original", "Original-Kali-Bootscreen (Kali-Standard)")
    modus.set_active_id(cfg["modus"])
    abschnitt("Art des Ladebildschirms")
    studio.row(g, "Modus", modus, "„Original-Kali“ schaltet auf den normalen Kali-Ladebildschirm um; Einstellungen unten gelten dann nicht.")

    # ---------- Hintergrund ----------
    abschnitt("Hintergrund")
    hg = Gtk.ComboBoxText()
    for k, n in (("code", "Code-Regen (fallende Zeichen)"), ("schwarz", "Nur schwarz – nur das Logo"),
                 ("bild", "Bild (ohne Code)"), ("bild-code", "Bild + Code-Regen darüber")):
        hg.append(k, n)
    hg.set_active_id(cfg["hintergrund"])
    studio.row(g, "Hintergrund", hg)
    hg_bild = Gtk.ComboBoxText()
    hg_dunkel = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 95, 1); hg_dunkel.set_value(cfg["hg_dunkel"])
    hg_dunkel.set_size_request(260, -1); hg_dunkel._standard = STANDARD["hg_dunkel"]

    def hg_liste(aktiv=None):
        hg_bild.remove_all()
        try:
            for n in sorted(os.listdir(BILDER)):
                if n.startswith("hg-"):
                    hg_bild.append("@datei:" + n, "Eigenes Bild: " + n[3:])
        except OSError:
            pass
        try:
            for n in _generator().kali_hintergruende():
                hg_bild.append("@kali:" + n, "Kali: " + n)
        except Exception:
            pass
        hg_bild.set_active_id(aktiv or cfg["hg_bild"])
        if hg_bild.get_active_id() is None and hg_bild.get_model() is not None and len(hg_bild.get_model()):
            hg_bild.set_active(0)

    hg_liste()
    hg_zeile = Gtk.Box(spacing=8)
    hg_zeile.pack_start(hg_bild, True, True, 0)
    hg_neu = Gtk.Button(label="Bild vom PC wählen …")
    hg_zeile.pack_start(hg_neu, False, False, 0)
    studio.row(g, "Hintergrundbild", hg_zeile, "Kali-Bilder oder eigenes Bild (JPG/PNG).")
    studio.row(g, "Abdunkeln (%)", hg_dunkel, "Damit Logo und Text lesbar bleiben.")

    # ---------- Logos ----------
    abschnitt("Logos")
    logos = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=2)
    haken = {}
    status_l = Gtk.Label(xalign=0, wrap=True)

    def logo_optionen():
        out = list(KALI_LOGOS)
        out += [("datei:" + n, "Bild: " + n[5:]) for n in cfg["dateilogos"]]
        out += [(k, n) for k, n in studio.logo_choices_list() if k != "aus"]
        return [(k, n) for k, n in out if k not in cfg["verborgen"]]

    def logos_neu(setze=None):
        vorher = {k for k, b in haken.items() if b.get_active()} or set(cfg["logo_keys"])
        if setze:
            vorher.add(setze)
        for ch in logos.get_children():
            ch.destroy()
        haken.clear()
        for key, name in logo_optionen():
            box = Gtk.Box(spacing=4)
            cb = Gtk.CheckButton(label=name); cb.set_active(key in vorher)
            cb.connect("toggled", vorschau_planen)
            x = Gtk.Button(label="✕"); x.set_tooltip_text("Logo löschen / ausblenden"); x.set_relief(Gtk.ReliefStyle.NONE)
            x.connect("clicked", logo_loeschen, key, name)
            box.pack_start(cb, True, True, 0); box.pack_start(x, False, False, 0)
            logos.add(box); haken[key] = cb
        logos.show_all()

    def logo_loeschen(_b, key, name):
        d = Gtk.MessageDialog(transient_for=studio, modal=True, message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.YES_NO, text="Logo „%s“ entfernen?" % name)
        eigen = key.startswith("user:") or key.startswith("datei:")
        d.format_secondary_text("Eigenes Logo wird gelöscht." if eigen else
                                "Mitgeliefertes Logo wird nur ausgeblendet (Knopf „Ausgeblendete zurückholen“).")
        ja = d.run() == Gtk.ResponseType.YES
        d.destroy()
        if not ja:
            return
        if key.startswith("user:"):
            studio.eigene_logos_loeschen([key[5:]])
            studio.save(None, False, quiet=True)
        elif key.startswith("datei:"):
            n = key[6:]
            cfg["dateilogos"] = [x for x in cfg["dateilogos"] if x != n]
            try:
                os.remove(os.path.join(BILDER, n))
            except OSError:
                pass
        else:
            cfg["verborgen"] = sorted(set(cfg["verborgen"]) | {key})
        haken.pop(key, None)
        logos_neu(); vorschau_planen()
        status_l.set_text("„%s“ entfernt." % name)

    logo_zeile = Gtk.Box(spacing=8)
    logo_add = Gtk.Button(label="Logo aus Bild vom PC hinzufügen …")
    zurueck = Gtk.Button(label="Ausgeblendete zurückholen")
    logo_zeile.pack_start(logo_add, False, False, 0); logo_zeile.pack_start(zurueck, False, False, 0)
    studio.row(g, "Logos (mehrere = wechseln)", logos, "Nichts angekreuzt = Kali Drache. ✕ löscht bzw. blendet aus.")
    studio.row(g, "", logo_zeile)
    studio.row(g, "", status_l)

    # ---------- Farbe / Größe ----------
    abschnitt("Farbe und Größe")
    farbe = Gtk.ComboBoxText()
    farbe.append("regenbogen", "Regenbogen"); farbe.append("eine", "Eine Farbe")
    farbe.set_active_id(cfg["farbe"])
    studio.row(g, "Farbart (Code, Logo, Text)", farbe, "Regenbogen färbt Code, Logo und Text unter dem Logo.")
    kb = Gtk.ColorButton(); c1 = Gdk.RGBA(); c1.parse(cfg["farbe1"]); kb.set_rgba(c1)
    studio.row(g, "Farbe (bei „Eine Farbe“)", kb)
    dichte = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 120, 1); dichte.set_value(cfg["dichte"])
    dichte.set_size_request(260, -1); dichte._standard = STANDARD["dichte"]
    studio.row(g, "Wie viel Code fällt", dichte)
    hoehe = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 100, 900, 10); hoehe.set_value(cfg["logo_hoehe"])
    hoehe.set_size_request(260, -1); hoehe._standard = STANDARD["logo_hoehe"]
    studio.row(g, "Logo-Höhe (Pixel)", hoehe)

    # ---------- Text unter dem Logo ----------
    abschnitt("Text unter dem Logo (Code-Schrift)")
    unter = Gtk.Entry(text=cfg["unterschrift"]); unter.set_placeholder_text("z. B. KALI LINUX")
    studio.row(g, "Text", unter, "Leer = kein Text unter dem Logo.")
    ufont = Gtk.ComboBoxText()
    for f in FIGLET_FONTS:
        if f == "plain" or os.path.exists("/usr/share/figlet/%s.flf" % f):
            ufont.append(f, "Klartext (kein ASCII-Symbol)" if f == "plain" else "Code-Schrift: " + f)
    ufont.set_active_id(cfg["unterschrift_font"])
    studio.row(g, "Schriftart", ufont)
    ugr = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 8, 48, 1); ugr.set_value(cfg["unterschrift_groesse"])
    ugr.set_size_request(260, -1); ugr._standard = STANDARD["unterschrift_groesse"]
    studio.row(g, "Größe", ugr)

    # ---------- Start-Text ----------
    abschnitt("Start-Text (oben links, wie Terminal)")
    zeilen = Gtk.TextView(); zeilen.set_monospace(True)
    zeilen.get_buffer().set_text(cfg["startzeilen"])
    zs = Gtk.ScrolledWindow(); zs.add(zeilen); zs.set_size_request(420, 90)
    studio.row(g, "Text vor dem Start", zs, "Eine Zeile pro Zeile, höchstens 12. Leer = kein Text.")
    zk = Gtk.ColorButton(); c2 = Gdk.RGBA(); c2.parse(cfg["zeilen_farbe"]); zk.set_rgba(c2)
    studio.row(g, "Farbe des Start-Texts", zk)
    zreg = Gtk.Switch(active=bool(cfg["zeilen_regenbogen"]), halign=Gtk.Align.START)
    studio.row(g, "Start-Text im Regenbogen", zreg)
    zgr = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 10, 40, 1); zgr.set_value(cfg["startzeilen_groesse"])
    zgr.set_size_request(260, -1); zgr._standard = STANDARD["startzeilen_groesse"]
    studio.row(g, "Größe des Start-Texts", zgr)

    # ---------- Eigene Schrift ----------
    abschnitt("Eigene Schrift")
    schrift_label = Gtk.Label(xalign=0)
    sw_zeile = Gtk.Box(spacing=8)
    schrift_neu = Gtk.Button(label="Schrift wählen (.ttf/.otf) …")
    schrift_weg = Gtk.Button(label="Standard-Schrift")
    sw_zeile.pack_start(schrift_label, True, True, 0); sw_zeile.pack_start(schrift_neu, False, False, 0)
    sw_zeile.pack_start(schrift_weg, False, False, 0)
    studio.row(g, "Schrift", sw_zeile, "Gilt für Text unter dem Logo, Start-Text und Randtexte.")
    zustand_schrift = {"wert": cfg["schrift"]}

    def schrift_zeigen():
        w = zustand_schrift["wert"]
        schrift_label.set_text(w[7:] if w.startswith("@datei:") else "Standard (DejaVu Sans Mono)")

    schrift_zeigen()

    # ---------- Randtexte ----------
    abschnitt("Texte am Rand")
    texte = Gtk.Entry(text=cfg["texte"])
    studio.row(g, "Texte links und rechts", texte, "Leer lassen = keine Texte am Rand (empfohlen). Mit Komma trennen, höchstens 8.")

    status = Gtk.Label(xalign=0, wrap=True)
    studio.row(g, "", status)

    # ---------- Werte ----------
    def hex_von(btn):
        r = btn.get_rgba()
        return "#%02x%02x%02x" % (int(r.red * 255), int(r.green * 255), int(r.blue * 255))

    def zeilen_text():
        b = zeilen.get_buffer()
        return b.get_text(b.get_start_iter(), b.get_end_iter(), False)

    def werte():
        return {"modus": modus.get_active_id(), "farbe": farbe.get_active_id(), "farbe1": hex_von(kb),
                "dichte": int(dichte.get_value()), "logo_hoehe": int(hoehe.get_value()),
                "logo_keys": [k for k, b in haken.items() if b.get_active()][:8], "texte": texte.get_text(),
                "startzeilen": zeilen_text(), "zeilen_farbe": hex_von(zk), "zeilen_regenbogen": zreg.get_active(),
                "startzeilen_groesse": int(zgr.get_value()), "hintergrund": hg.get_active_id(),
                "hg_bild": hg_bild.get_active_id() or "", "hg_dunkel": int(hg_dunkel.get_value()),
                "unterschrift": unter.get_text(), "unterschrift_font": ufont.get_active_id() or "slant",
                "unterschrift_groesse": int(ugr.get_value()), "schrift": zustand_schrift["wert"],
                "dateilogos": cfg["dateilogos"], "verborgen": cfg["verborgen"]}

    def figlet_zeilen(text, font):
        text = text.strip()
        if not text:
            return []
        if font == "plain":
            return [text[:140]]
        try:
            out = subprocess.run(["figlet", "-w", "130", "-f", font, text], capture_output=True, text=True,
                                 timeout=3).stdout.rstrip("\n").split("\n")
            return [l[:140] for l in out][:14]
        except Exception:
            return [text[:140]]

    def daten_von(neu):
        keys = neu["logo_keys"] or ["kali-original"]
        return {"modus": neu["modus"], "farbe": neu["farbe"], "farbe1": neu["farbe1"], "dichte": neu["dichte"],
                "logo_hoehe": neu["logo_hoehe"], "logos": [art_von(k) for k in keys],
                "texte": [t.strip() for t in neu["texte"].split(",") if t.strip()][:8],
                "startzeilen": [z for z in neu["startzeilen"].split("\n") if z.strip()][:12],
                "zeilen_farbe": neu["zeilen_farbe"], "zeilen_regenbogen": neu["zeilen_regenbogen"],
                "startzeilen_groesse": neu["startzeilen_groesse"], "hintergrund": neu["hintergrund"],
                "hg_bild": neu["hg_bild"], "hg_dunkel": neu["hg_dunkel"],
                "unterschrift": figlet_zeilen(neu["unterschrift"], neu["unterschrift_font"]),
                "unterschrift_groesse": neu["unterschrift_groesse"], "schrift": neu["schrift"]}

    # ---------- Vorschau ----------
    zustand = {"timer": 0, "laeuft": False, "neu": False}

    def vorschau_zeichnen():
        zustand["timer"] = 0
        if zustand["laeuft"]:
            zustand["neu"] = True
            return False
        if modus.get_active_id() == "kali-original":
            vorschau_status.set_text("Original-Kali-Bootscreen: keine eigene Vorschau, es gilt das normale Kali-Logo mit Ladebalken.")
            return False
        zustand["laeuft"] = True
        try:
            d = daten_von(werte())
        except Exception as e:      # sonst bliebe "läuft" für immer an und die Vorschau fröre ein
            zustand["laeuft"] = False
            vorschau_status.set_text("Vorschau nicht möglich: %s" % e)
            return False
        arts = d.pop("logos"); d.pop("modus", None)

        def arbeit():
            try:
                bild = _generator().vorschau(d, arts, 460, 259)
                pb = GdkPixbuf.Pixbuf.new_from_data(bild.tobytes(), GdkPixbuf.Colorspace.RGB, False, 8, bild.width,
                                                    bild.height, bild.width * 3)
                GLib.idle_add(lambda: (vorschau_bild.set_from_pixbuf(pb.copy()), False)[1])
                GLib.idle_add(vorschau_status.set_text, "Vorschau (ungefähr): erstes angekreuztes Logo, so wie beim Start.")
            except Exception as e:
                GLib.idle_add(vorschau_status.set_text, "Vorschau nicht möglich: %s" % e)
            finally:
                zustand["laeuft"] = False
                if zustand["neu"]:
                    zustand["neu"] = False
                    GLib.idle_add(vorschau_planen)
        threading.Thread(target=arbeit, daemon=True).start()
        return False

    def vorschau_planen(*_a):
        if zustand["timer"]:
            GLib.source_remove(zustand["timer"])
        zustand["timer"] = GLib.timeout_add(500, vorschau_zeichnen)
        return False

    for w, sig in ((modus, "changed"), (hg, "changed"), (hg_bild, "changed"), (farbe, "changed"), (ufont, "changed"),
                   (kb, "color-set"), (zk, "color-set"), (dichte, "value-changed"), (hoehe, "value-changed"),
                   (hg_dunkel, "value-changed"), (ugr, "value-changed"), (zgr, "value-changed"),
                   (texte, "changed"), (unter, "changed"), (zreg, "notify::active")):
        w.connect(sig, vorschau_planen)
    zeilen.get_buffer().connect("changed", vorschau_planen)

    # ---------- Knöpfe für Dateien ----------
    def bild_als_hintergrund(_b):
        p = _datei_waehlen(studio, "Hintergrundbild wählen", [".jpg", ".jpeg", ".png"])
        if p:
            try:
                n = _kopieren(p, "hg-")
                hg_liste("@datei:" + n)
                if hg.get_active_id() in ("code", "schwarz"):
                    hg.set_active_id("bild")
            except OSError as e:
                status.set_text("Bild konnte nicht kopiert werden: %s" % e)
            vorschau_planen()

    def bild_als_logo(_b):
        p = _datei_waehlen(studio, "Logo-Bild wählen (am besten PNG mit transparentem Hintergrund)",
                           [".png", ".jpg", ".jpeg"])
        if p:
            try:
                n = _kopieren(p, "logo-")
                if n not in cfg["dateilogos"]:
                    cfg["dateilogos"].append(n)
                logos_neu("datei:" + n)
            except OSError as e:
                status_l.set_text("Bild konnte nicht kopiert werden: %s" % e)
            vorschau_planen()

    def logos_zurueck(_b):
        cfg["verborgen"] = []
        logos_neu(); vorschau_planen()

    def schrift_waehlen(_b):
        p = _datei_waehlen(studio, "Schrift wählen", [".ttf", ".otf"])
        if p:
            try:
                zustand_schrift["wert"] = "@datei:" + _kopieren(p, "schrift-")
                schrift_zeigen(); vorschau_planen()
            except OSError as e:
                status.set_text("Schrift konnte nicht kopiert werden: %s" % e)

    def schrift_standard(_b):
        zustand_schrift["wert"] = ""; schrift_zeigen(); vorschau_planen()

    hg_neu.connect("clicked", bild_als_hintergrund)
    logo_add.connect("clicked", bild_als_logo)
    zurueck.connect("clicked", logos_zurueck)
    schrift_neu.connect("clicked", schrift_waehlen)
    schrift_weg.connect("clicked", schrift_standard)

    logos_neu()
    GLib.timeout_add(300, vorschau_zeichnen)

    # ---------- Speichern / Anwenden ----------
    def aktion(_w, zuruecksetzen=False):
        neu = werte()
        if not zuruecksetzen:
            os.makedirs(os.path.dirname(CFG), exist_ok=True)
            with open(CFG, "w") as f:
                json.dump(neu, f)
        daten = daten_von(neu)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(daten, f); tmp = f.name
        os.chmod(tmp, 0o644)
        cmd = ["pkexec", "/usr/local/sbin/terminal-studio-boot", "--zuruecksetzen"] if zuruecksetzen \
            else ["pkexec", "/usr/local/sbin/terminal-studio-boot", tmp]
        status.set_text("Wird erzeugt … das dauert etwa eine Minute. Bitte Passwort eingeben.")

        def arbeit():
            r = subprocess.run(cmd, capture_output=True, text=True)
            try:
                os.remove(tmp)
            except OSError:
                pass
            GLib.idle_add(status.set_text, "Fertig. Beim nächsten Start siehst du den neuen Ladebildschirm."
                          if r.returncode == 0 else "Hat nicht geklappt: " + (r.stderr or r.stdout).strip()[-200:])
        threading.Thread(target=arbeit, daemon=True).start()

    bx = Gtk.Box(spacing=8)
    b1 = Gtk.Button(label="Speichern und anwenden"); b1.connect("clicked", aktion)
    b2 = Gtk.Button(label="Zurück zum Original"); b2.connect("clicked", aktion, True)
    b3 = Gtk.Button(label="Ladebildschirm testen (20 s)")
    b3.set_tooltip_text("Zeigt den zuletzt angewendeten Ladebildschirm 20 Sekunden im Vollbild. Esc bricht ab.")

    def testen(_w):
        try:
            subprocess.Popen(["pkexec", "/usr/local/sbin/ladebildschirm-test", "20"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as e:
            status.set_text("Test nicht möglich: %s" % e)
            return
        status.set_text("Test läuft: 20 Sekunden im Vollbild. Mit Esc abbrechen.")
        b3.set_sensitive(False)
        GLib.timeout_add_seconds(24, lambda: (b3.set_sensitive(True), False)[1])

    b3.connect("clicked", testen)
    bx.pack_start(b1, False, False, 0); bx.pack_start(b2, False, False, 0); bx.pack_start(b3, False, False, 0)
    studio.row(g, "", bx, "Der Test zeigt den zuletzt angewendeten Ladebildschirm. Änderungen erst mit „Speichern und anwenden“ (dauert etwa eine Minute).")
    return g
