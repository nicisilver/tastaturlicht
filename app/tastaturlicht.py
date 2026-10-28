#!/usr/bin/env python3
# tastaturlicht.py – Mein Farb-Programm für das Tastaturlicht 💜
#
# Es schreibt in die "Brücke" aus Lektion 8:
#   /sys/class/leds/pink_tastatur::kbd_backlight/multi_intensity  (Farbe)
#   /sys/class/leds/pink_tastatur::kbd_backlight/brightness       (Helligkeit)
# Dank der Erlaubnis-Regel aus Lektion 9 geht das ohne Passwort.

import json
import os
import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk

LICHT = "/sys/class/leds/pink_tastatur::kbd_backlight"
FARBE_MAX = 50        # mein EC zählt pro Farbe nur bis 50
HELLIGKEIT_MAX = 4

# Schnell-Knöpfe: Name, Farbe für den Bildschirm, Werte für den Chip (0–50)
# Das sind nur die Start-Farben. Sobald du in der App etwas änderst,
# landen deine eigenen in ~/.config/tastaturlicht/lieblingsfarben.json
LIEBLINGSFARBEN = [
    ("Lila",      "#b26cff", (30, 0, 50)),
    ("Pink",      "#ff4fa3", (50, 15, 32)),
    ("Rosa",      "#ffa3c8", (50, 25, 35)),
    ("Pfirsich",  "#ffb38a", (50, 22, 10)),
    ("Mint",      "#7ee8c4", (10, 50, 30)),
    ("Himmel",    "#89c4ff", (10, 30, 50)),
    ("Türkis",    "#3fe0e0", (0, 50, 50)),
    ("Weiß",      "#ffffff", (50, 50, 50)),
]


# ---------- Mit der Brücke reden ----------

def lesen(name):
    with open(f"{LICHT}/{name}") as datei:
        return datei.read().strip()


def schreiben(name, text):
    with open(f"{LICHT}/{name}", "w") as datei:
        datei.write(text)


def chip_zu_bildschirm(r, g, b):
    """0–50 (Chip) -> Gdk.RGBA (Bildschirm, 0.0–1.0)"""
    farbe = Gdk.RGBA()
    farbe.red, farbe.green, farbe.blue, farbe.alpha = r / FARBE_MAX, g / FARBE_MAX, b / FARBE_MAX, 1.0
    return farbe


def bildschirm_zu_chip(farbe):
    """Gdk.RGBA (0.0–1.0) -> 0–50 (Chip)"""
    return tuple(round(wert * FARBE_MAX) for wert in (farbe.red, farbe.green, farbe.blue))


def zu_hex(farbe):
    """Gdk.RGBA -> "#rrggbb" """
    return "#{:02x}{:02x}{:02x}".format(*(round(w * 255) for w in (farbe.red, farbe.green, farbe.blue)))


# ---------- Lieblingsfarben merken ----------

FARBEN_DATEI = os.path.join(GLib.get_user_config_dir(), "tastaturlicht", "lieblingsfarben.json")


def lade_lieblingsfarben():
    try:
        with open(FARBEN_DATEI) as datei:
            return [(name, farbe, tuple(chip)) for name, farbe, chip in json.load(datei)]
    except (OSError, ValueError):
        return list(LIEBLINGSFARBEN)     # noch nichts gespeichert -> Start-Farben


def speichere_lieblingsfarben(farben):
    os.makedirs(os.path.dirname(FARBEN_DATEI), exist_ok=True)
    with open(FARBEN_DATEI, "w") as datei:
        json.dump(farben, datei, ensure_ascii=False, indent=2)


# ---------- Katzenpfote malen 🐾 ----------

# Ein großer Ballen unten, vier Zehen oben – {farbe} wird ausgetauscht
PFOTE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 64 64">
  <g fill="{farbe}" stroke="#000" stroke-opacity="0.18" stroke-width="1.5">
    <ellipse cx="32" cy="45" rx="15" ry="12"/>
    <ellipse cx="13" cy="27" rx="6" ry="7.5" transform="rotate(-23 13 27)"/>
    <ellipse cx="24" cy="16" rx="6" ry="7.5" transform="rotate(-9 24 16)"/>
    <ellipse cx="40" cy="16" rx="6" ry="7.5" transform="rotate(9 40 16)"/>
    <ellipse cx="51" cy="27" rx="6" ry="7.5" transform="rotate(23 51 27)"/>
  </g>
  <g fill="#fff" fill-opacity="0.5">
    <ellipse cx="26" cy="40" rx="4.5" ry="2.6"/>
    <ellipse cx="11" cy="24" rx="1.8" ry="1.6"/>
    <ellipse cx="22" cy="13" rx="1.8" ry="1.6"/>
    <ellipse cx="38" cy="13" rx="1.8" ry="1.6"/>
    <ellipse cx="49" cy="24" rx="1.8" ry="1.6"/>
  </g>
</svg>"""


def pfote(bildschirmfarbe):
    """Macht ein Pfoten-Bild in der gewünschten Farbe."""
    svg = PFOTE_SVG.replace("{farbe}", bildschirmfarbe)
    bild = Gdk.Texture.new_from_bytes(GLib.Bytes.new(svg.encode()))
    return Gtk.Image(paintable=bild, pixel_size=60)


# Katzenkopf für die Vorschau – leuchtet in der eingestellten Farbe.
# Das Gesicht kommt danach extra.
KATZE_KOPF = """<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="schein">
      <stop offset="0.4" stop-color="{farbe}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="{farbe}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="52" r="48" fill="url(#schein)"/>
  <g fill="{farbe}" stroke="#000" stroke-opacity="0.18" stroke-width="1.5" stroke-linejoin="round">
    <path d="M20 46 L25 12 L47 30 Z"/>
    <path d="M80 46 L75 12 L53 30 Z"/>
    <ellipse cx="50" cy="57" rx="34" ry="28"/>
  </g>
  <g fill="#fff" fill-opacity="0.35">
    <path d="M26 36 L28 19 L39 29 Z"/>
    <path d="M74 36 L72 19 L61 29 Z"/>
  </g>
  <g fill="none" stroke="#2b2233" stroke-width="1.4" stroke-linecap="round" stroke-opacity="0.5">
    <path d="M24 58 L10 55 M24 62 L10 63"/>
    <path d="M76 58 L90 55 M76 62 L90 63"/>
  </g>
  <g fill="#ff7fb0" fill-opacity="0.45">
    <ellipse cx="29" cy="62" rx="5" ry="3"/>
    <ellipse cx="71" cy="62" rx="5" ry="3"/>
  </g>
"""

# Normale Katze: Knopfaugen und ω-Mund
KATZE_GESICHT = """
  <g fill="#2b2233">
    <ellipse cx="38" cy="53" rx="3.6" ry="4.6"/>
    <ellipse cx="62" cy="53" rx="3.6" ry="4.6"/>
    <path d="M47 61 L53 61 L50 64.5 Z"/>
  </g>
  <g fill="#fff">
    <circle cx="39.2" cy="51.4" r="1.3"/>
    <circle cx="63.2" cy="51.4" r="1.3"/>
  </g>
  <path d="M44 65.5 Q47 69 50 65.5 Q53 69 56 65.5" fill="none" stroke="#2b2233"
        stroke-width="1.4" stroke-linecap="round"/>
</svg>"""

# Trottel-Katze: Glubschaugen, die in verschiedene Richtungen schauen, und Zunge raus
TROTTEL_KATZE_GESICHT = """
  <circle cx="37" cy="52" r="8" fill="#fff" stroke="#2b2233" stroke-width="1"/>
  <circle cx="63" cy="53" r="5.5" fill="#fff" stroke="#2b2233" stroke-width="1"/>
  <circle cx="33.5" cy="49" r="3.4" fill="#2b2233"/>
  <circle cx="66" cy="55.5" r="2.5" fill="#2b2233"/>
  <path d="M47 61 L53 61 L50 64.5 Z" fill="#2b2233"/>
  <path d="M48 67.5 q-1 7 3 7 q4 0 2.5 -7 Z" fill="#ff7fb0" stroke="#2b2233" stroke-width="0.8"/>
  <path d="M43 66 Q47 69.5 50 66.5 Q53 69.5 57 66" fill="none" stroke="#2b2233"
        stroke-width="1.4" stroke-linecap="round"/>
</svg>"""


# Waschbär-Kopf mit Maske – das Gesicht kommt danach extra
WASCHBAER_KOPF = """<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="schein">
      <stop offset="0.4" stop-color="{farbe}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="{farbe}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="52" r="48" fill="url(#schein)"/>
  <g fill="{farbe}" stroke="#000" stroke-opacity="0.18" stroke-width="1.5" stroke-linejoin="round">
    <ellipse cx="25" cy="28" rx="10" ry="12" transform="rotate(-25 25 28)"/>
    <ellipse cx="75" cy="28" rx="10" ry="12" transform="rotate(25 75 28)"/>
    <path d="M17 54 L5 66 L22 66 Z"/>
    <path d="M83 54 L95 66 L78 66 Z"/>
    <ellipse cx="50" cy="56" rx="35" ry="28"/>
  </g>
  <g fill="#2b2233" fill-opacity="0.75">
    <ellipse cx="25" cy="29" rx="5" ry="7" transform="rotate(-25 25 29)"/>
    <ellipse cx="75" cy="29" rx="5" ry="7" transform="rotate(25 75 29)"/>
  </g>
  <g fill="#fff" fill-opacity="0.8">
    <ellipse cx="34" cy="43" rx="9" ry="4.5" transform="rotate(-12 34 43)"/>
    <ellipse cx="66" cy="43" rx="9" ry="4.5" transform="rotate(12 66 43)"/>
  </g>
  <path d="M48 30 Q50 42 50 52 Q50 42 52 30 Z" fill="#2b2233" fill-opacity="0.6"/>
  <path d="M17 56 Q28 44 44 51 Q50 54 56 51 Q72 44 83 56 Q72 66 57 61 Q50 59 43 61 Q28 66 17 56 Z" fill="#2b2233"/>
"""

# Trotteliger Waschbär: schielt ein bisschen und streckt die Zunge raus
TROTTEL_GESICHT = """
  <circle cx="35" cy="55" r="7.5" fill="#fff"/>
  <circle cx="65" cy="54" r="5.5" fill="#fff"/>
  <circle cx="38" cy="57" r="3.2" fill="#2b2233"/>
  <circle cx="62.5" cy="52.5" r="2.4" fill="#2b2233"/>
  <ellipse cx="50" cy="69" rx="13" ry="8.5" fill="#fff"/>
  <ellipse cx="50" cy="64" rx="4.5" ry="3" fill="#2b2233"/>
  <path d="M51 72 q0 6 3.5 5.5 q2.5 -0.5 1.5 -6 Z" fill="#ff7fb0" stroke="#2b2233" stroke-width="0.8"/>
  <path d="M42 71 Q50 75 58 71" fill="none" stroke="#2b2233" stroke-width="1.4" stroke-linecap="round"/>
  <rect x="45" y="72.3" width="3" height="3.2" rx="0.6" fill="#fff" stroke="#2b2233" stroke-width="0.6"/>
</svg>"""

# Normaler Waschbär: gleich große Augen, kleines Lächeln
NORMAL_GESICHT = """
  <circle cx="35" cy="55" r="5" fill="#fff"/>
  <circle cx="65" cy="55" r="5" fill="#fff"/>
  <circle cx="35.5" cy="55.5" r="3" fill="#2b2233"/>
  <circle cx="64.5" cy="55.5" r="3" fill="#2b2233"/>
  <circle cx="36.5" cy="54.3" r="1" fill="#fff"/>
  <circle cx="65.5" cy="54.3" r="1" fill="#fff"/>
  <ellipse cx="50" cy="69" rx="13" ry="8.5" fill="#fff"/>
  <ellipse cx="50" cy="64" rx="4.5" ry="3" fill="#2b2233"/>
  <path d="M50 67 L50 70 M45 70 Q47.5 73 50 70 Q52.5 73 55 70" fill="none" stroke="#2b2233"
        stroke-width="1.4" stroke-linecap="round"/>
</svg>"""

# Welche Tierchen man oben als Vorschau auswählen kann
TIERE = {
    "Katze": KATZE_KOPF + KATZE_GESICHT,
    "Trottel-Katze": KATZE_KOPF + TROTTEL_KATZE_GESICHT,
    "Waschbär": WASCHBAER_KOPF + NORMAL_GESICHT,
    "Trottel-Waschbär": WASCHBAER_KOPF + TROTTEL_GESICHT,
}


def tierbild(tier, hex_farbe):
    svg = TIERE[tier].replace("{farbe}", hex_farbe)
    return Gdk.Texture.new_from_bytes(GLib.Bytes.new(svg.encode()))


# ---------- Das Fenster ----------

class Fenster(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Tastaturlicht")
        self.set_default_size(420, 560)

        # Das Schreiben dauert ein bisschen (der Chip ist langsam).
        # Damit das Fenster nicht hängt, schreibt ein Helfer im Hintergrund.
        self.wunsch = None              # was zuletzt eingestellt wurde
        self.wunsch_schloss = threading.Lock()
        self.helfer_laeuft = False
        self.wird_geladen = True        # beim Start nichts zurückschreiben

        kopf = Adw.HeaderBar()
        self.toasts = Adw.ToastOverlay()

        ansicht = Adw.ToolbarView()
        ansicht.add_top_bar(kopf)
        ansicht.set_content(self.toasts)
        self.set_content(ansicht)

        try:
            r, g, b = (int(x) for x in lesen("multi_intensity").split())
            helligkeit = int(lesen("brightness"))
        except OSError:
            self.zeige_fehler()
            return

        self.baue_inhalt(r, g, b, helligkeit)
        self.wird_geladen = False

    def zeige_fehler(self):
        seite = Adw.StatusPage(
            icon_name="keyboard-brightness-symbolic",
            title="Treiber nicht geladen 😿",
            description="Bitte im Terminal eingeben:\n\n"
                        "sudo modprobe pink_tastatur",
        )
        self.toasts.set_child(seite)

    def baue_inhalt(self, r, g, b, helligkeit):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24,
                      margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)

        # Große Vorschau-Fläche
        self.vorschau = Gtk.Image(pixel_size=120, halign=Gtk.Align.CENTER)
        box.append(self.vorschau)

        # Schnell-Knöpfe in einem Raster, mit ➕ und ✏️ oben rechts
        self.lieblingsfarben = lade_lieblingsfarben()

        neu_knopf = Gtk.Button(icon_name="list-add-symbolic", css_classes=["flat"],
                               tooltip_text="Aktuelle Farbe als Lieblingsfarbe speichern")
        neu_knopf.connect("clicked", lambda _: self.farbe_bearbeiten(None))
        self.bearbeiten_knopf = Gtk.ToggleButton(icon_name="document-edit-symbolic", css_classes=["flat"],
                                                 tooltip_text="Lieblingsfarben bearbeiten")
        self.bearbeiten_knopf.connect("toggled", self.bearbeiten_umgeschaltet)
        knoepfe = Gtk.Box(spacing=6)
        knoepfe.append(neu_knopf)
        knoepfe.append(self.bearbeiten_knopf)

        self.gruppe_schnell = Adw.PreferencesGroup(title="Lieblingsfarben", header_suffix=knoepfe)
        self.raster = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,
                                  max_children_per_line=4, min_children_per_line=4,
                                  column_spacing=12, row_spacing=12, homogeneous=True)
        self.raster_fuellen()
        self.gruppe_schnell.add(self.raster)
        box.append(self.gruppe_schnell)

        # Eigene Farbe + Helligkeit
        gruppe_eigene = Adw.PreferencesGroup(title="Einstellen")

        self.farbwaehler = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False),
                                                 valign=Gtk.Align.CENTER)
        self.farbwaehler.set_rgba(chip_zu_bildschirm(r, g, b))
        self.farbwaehler.connect("notify::rgba", self.farbe_gewaehlt)
        zeile_farbe = Adw.ActionRow(title="Eigene Farbe", subtitle="Jede Farbe, die du magst 🎨")
        zeile_farbe.add_suffix(self.farbwaehler)
        gruppe_eigene.add(zeile_farbe)

        self.regler = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, HELLIGKEIT_MAX, 1)
        self.regler.set_hexpand(True)
        self.regler.set_draw_value(False)
        for stufe in range(HELLIGKEIT_MAX + 1):
            self.regler.add_mark(stufe, Gtk.PositionType.BOTTOM, None)
        self.regler.set_value(helligkeit)
        self.regler.connect("value-changed", self.helligkeit_geaendert)
        zeile_hell = Adw.ActionRow(title="Helligkeit")
        zeile_hell.add_suffix(self.regler)
        gruppe_eigene.add(zeile_hell)

        self.tierwahl = Adw.ComboRow(title="Tierchen", subtitle="Wer soll oben leuchten?",
                                     model=Gtk.StringList.new(list(TIERE)))
        self.tierwahl.connect("notify::selected", self.tier_gewaehlt)
        gruppe_eigene.add(self.tierwahl)

        box.append(gruppe_eigene)

        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, child=box)
        self.toasts.set_child(scroller)
        self.vorschau_faerben(self.farbwaehler.get_rgba())

    def raster_fuellen(self):
        self.raster.remove_all()
        for nummer, (name, bildschirmfarbe, _) in enumerate(self.lieblingsfarben):
            knopf = Gtk.Button(tooltip_text=name, css_classes=["pfotenknopf"],
                               child=pfote(bildschirmfarbe), halign=Gtk.Align.CENTER)
            knopf.connect("clicked", self.pfote_geklickt, nummer)
            beschriftung = Gtk.Label(label=name, css_classes=["caption"])
            zelle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            zelle.append(knopf)
            zelle.append(beschriftung)
            self.raster.append(zelle)

    # ----- Wenn etwas geklickt wird -----

    def pfote_geklickt(self, knopf, nummer):
        if self.bearbeiten_knopf.get_active():
            self.farbe_bearbeiten(nummer)
        else:
            # Setzt den Farbwähler, der löst dann farbe_gewaehlt aus
            chipwerte = self.lieblingsfarben[nummer][2]
            self.farbwaehler.set_rgba(chip_zu_bildschirm(*chipwerte))

    def bearbeiten_umgeschaltet(self, knopf):
        if knopf.get_active():
            self.gruppe_schnell.set_description("Tippe auf eine Pfote, um sie zu ändern ✏️")
        else:
            self.gruppe_schnell.set_description(None)

    # ----- Lieblingsfarbe ändern oder neu anlegen -----

    def farbe_bearbeiten(self, nummer):
        """nummer = welche Pfote, None = eine neue mit der aktuellen Farbe"""
        if nummer is None:
            aktuell = self.farbwaehler.get_rgba()
            name, bildschirmfarbe, chipwerte = "", zu_hex(aktuell), bildschirm_zu_chip(aktuell)
        else:
            name, bildschirmfarbe, chipwerte = self.lieblingsfarben[nummer]

        namensfeld = Adw.EntryRow(title="Name", text=name)
        startfarbe = Gdk.RGBA()
        startfarbe.parse(bildschirmfarbe)
        waehler = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog(with_alpha=False),
                                        rgba=startfarbe, valign=Gtk.Align.CENTER)
        # Beim Aussuchen leuchtet die Tastatur gleich mit
        waehler.connect("notify::rgba", lambda w, _: self.farbwaehler.set_rgba(w.get_rgba()))
        zeile_farbe = Adw.ActionRow(title="Farbe", activatable_widget=waehler)
        zeile_farbe.add_suffix(waehler)

        liste = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        liste.append(namensfeld)
        liste.append(zeile_farbe)

        dialog = Adw.AlertDialog(heading="Neue Lieblingsfarbe" if nummer is None else "Lieblingsfarbe ändern",
                                 extra_child=liste)
        dialog.add_response("abbrechen", "Abbrechen")
        if nummer is not None:
            dialog.add_response("loeschen", "Löschen")
            dialog.set_response_appearance("loeschen", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.add_response("speichern", "Speichern")
        dialog.set_response_appearance("speichern", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("speichern")
        dialog.set_close_response("abbrechen")
        dialog.connect("response", self.bearbeiten_fertig, nummer, namensfeld, waehler,
                       bildschirmfarbe, chipwerte)
        dialog.present(self)

    def bearbeiten_fertig(self, dialog, antwort, nummer, namensfeld, waehler, alte_farbe, chipwerte):
        if antwort == "abbrechen":
            return
        if antwort == "loeschen":
            del self.lieblingsfarben[nummer]
        else:
            neue_farbe = zu_hex(waehler.get_rgba())
            if neue_farbe != alte_farbe:     # Farbe geändert -> Chipwerte neu ausrechnen
                chipwerte = bildschirm_zu_chip(waehler.get_rgba())
            eintrag = (namensfeld.get_text().strip() or "Ohne Name", neue_farbe, chipwerte)
            if nummer is None:
                self.lieblingsfarben.append(eintrag)
            else:
                self.lieblingsfarben[nummer] = eintrag

        try:
            speichere_lieblingsfarben(self.lieblingsfarben)
        except OSError as fehler:
            self.meldung(f"Speichern hat nicht geklappt: {fehler.strerror}")
        self.raster_fuellen()

    def farbe_gewaehlt(self, *_):
        self.vorschau_faerben(self.farbwaehler.get_rgba())
        self.anwenden()

    def helligkeit_geaendert(self, *_):
        self.anwenden()

    def tier_gewaehlt(self, *_):
        self.vorschau_faerben(self.farbwaehler.get_rgba())

    def vorschau_faerben(self, farbe):
        tier = self.tierwahl.get_selected_item().get_string()
        self.vorschau.set_from_paintable(tierbild(tier, zu_hex(farbe)))

    # ----- An den Chip schicken (im Hintergrund) -----

    def anwenden(self):
        if self.wird_geladen:
            return
        r, g, b = bildschirm_zu_chip(self.farbwaehler.get_rgba())
        helligkeit = int(self.regler.get_value())
        with self.wunsch_schloss:
            self.wunsch = (r, g, b, helligkeit)
            if self.helfer_laeuft:
                return              # der Helfer nimmt sich gleich den neuesten Wunsch
            self.helfer_laeuft = True
        threading.Thread(target=self.helfer, daemon=True).start()

    def helfer(self):
        while True:
            with self.wunsch_schloss:
                wunsch, self.wunsch = self.wunsch, None
                if wunsch is None:
                    self.helfer_laeuft = False
                    return
            r, g, b, helligkeit = wunsch
            try:
                if r or g or b:     # alles 0 mag der Chip nicht (Sonderfall)
                    schreiben("multi_intensity", f"{r} {g} {b}")
                schreiben("brightness", str(helligkeit))   # "Übernehmen"-Knopf
            except OSError as fehler:
                GLib.idle_add(self.meldung, f"Hat nicht geklappt: {fehler.strerror}")

    def meldung(self, text):
        self.toasts.add_toast(Adw.Toast(title=text))
        return False


# ---------- Aussehen (CSS) ----------

STIL = """
.pfotenknopf { background: none; box-shadow: none; padding: 4px; border-radius: 9999px;
               transition: transform 150ms ease-out; }
.pfotenknopf:hover { background: alpha(currentColor, 0.08); transform: scale(1.15) rotate(-8deg); }
.pfotenknopf:active { transform: scale(0.9); }
"""



class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="de.nes.Tastaturlicht")

    def do_activate(self):
        stil = Gtk.CssProvider()
        stil.load_from_string(STIL)
        anzeige = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(anzeige, stil, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        fenster = self.props.active_window or Fenster(self)
        fenster.present()


if __name__ == "__main__":
    App().run()
