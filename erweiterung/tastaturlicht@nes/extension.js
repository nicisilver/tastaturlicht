// extension.js – Mini-Tastaturlicht im GNOME-Schnellmenü 💜
//
// Ein Knopf oben rechts im Schnellmenü (neben WLAN, Bluetooth …):
//   - Klick:          Licht an / aus
//   - Pfeil daneben:  Farbpunkte, Helligkeits-Regler und "Mehr Einstellungen …"
//
// Es schreibt in dieselbe Brücke wie mein Farb-Programm (Lektion 8 + 9).

import GObject from 'gi://GObject';
import Gio from 'gi://Gio';
import St from 'gi://St';
import Clutter from 'gi://Clutter';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {QuickMenuToggle, SystemIndicator} from 'resource:///org/gnome/shell/ui/quickSettings.js';
import {Slider} from 'resource:///org/gnome/shell/ui/slider.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const LICHT = '/sys/class/leds/pink_tastatur::kbd_backlight';
const HELLIGKEIT_MAX = 4;

// Dieselben Lieblingsfarben wie im Farb-Programm
const LIEBLINGSFARBEN = [
    ['Lila', '#b26cff', '30 0 50'],
    ['Pink', '#ff4fa3', '50 15 32'],
    ['Rosa', '#ffa3c8', '50 25 35'],
    ['Pfirsich', '#ffb38a', '50 22 10'],
    ['Mint', '#7ee8c4', '10 50 30'],
    ['Himmel', '#89c4ff', '10 30 50'],
    ['Türkis', '#3fe0e0', '0 50 50'],
    ['Weiß', '#ffffff', '50 50 50'],
];

// ---------- Mit der Brücke reden (ohne GNOME einzufrieren) ----------

// Schreiben über ein kleines Hilfsprogramm im Hintergrund.
// (Direkt schreiben würde GNOME kurz anhalten, weil der Chip langsam ist.)
function schreiben(name, text) {
    try {
        const helfer = Gio.Subprocess.new(
            ['/usr/bin/sh', '-c', 'printf "%s" "$1" > "$2"', 'sh', text, `${LICHT}/${name}`],
            Gio.SubprocessFlags.NONE);
        helfer.wait_async(null, null);
    } catch (fehler) {
        console.error(`Tastaturlicht: ${fehler.message}`);
    }
}

// Lesen im Hintergrund, Ergebnis kommt an "fertig"
function lesen(name, fertig) {
    const datei = Gio.File.new_for_path(`${LICHT}/${name}`);
    datei.load_contents_async(null, (quelle, ergebnis) => {
        try {
            const [, inhalt] = quelle.load_contents_finish(ergebnis);
            fertig(new TextDecoder().decode(inhalt).trim());
        } catch {
            fertig(null);   // Treiber nicht geladen
        }
    });
}

// ---------- Der Knopf im Schnellmenü ----------

const LichtKnopf = GObject.registerClass(
class LichtKnopf extends QuickMenuToggle {
    _init(erweiterung) {
        super._init({
            title: 'Tastatur',
            iconName: 'keyboard-brightness-symbolic',
            toggleMode: true,
        });
        this._erweiterung = erweiterung;
        this._stufe = HELLIGKEIT_MAX;     // zuletzt benutzte Helligkeit
        this._wirdGesetzt = false;        // damit wir nicht im Kreis schreiben

        this.menu.setHeader('keyboard-brightness-symbolic', 'Tastaturlicht', 'Finger weg, Leon! 😼');

        // Farbpunkte
        const punkteZeile = new PopupMenu.PopupBaseMenuItem({reactive: false, can_focus: false});
        const punkte = new St.BoxLayout({x_expand: true, x_align: Clutter.ActorAlign.CENTER,
            style_class: 'tastaturlicht-punkte'});
        for (const [name, farbe, werte] of LIEBLINGSFARBEN) {
            const punkt = new St.Button({
                style_class: 'tastaturlicht-punkt',
                style: `background-color: ${farbe};`,
                accessible_name: name,
                can_focus: true,
            });
            punkt.connect('clicked', () => this._farbeSetzen(werte));
            punkte.add_child(punkt);
        }
        punkteZeile.add_child(punkte);
        this.menu.addMenuItem(punkteZeile);

        // Helligkeits-Regler
        const reglerZeile = new PopupMenu.PopupBaseMenuItem({activate: false});
        reglerZeile.add_child(new St.Icon({icon_name: 'display-brightness-symbolic',
            style_class: 'popup-menu-icon'}));
        this._regler = new Slider(1);
        this._regler.x_expand = true;
        this._regler.connect('notify::value', () => this._reglerBewegt());
        reglerZeile.add_child(this._regler);
        this.menu.addMenuItem(reglerZeile);

        // Großes Programm öffnen
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const mehr = this.menu.addAction('Mehr Einstellungen …', () => {
            const app = Gio.DesktopAppInfo.new('tastaturlicht.desktop');
            app?.launch([], null);
            Main.panel.closeQuickSettings();
        });
        mehr.visible = Gio.DesktopAppInfo.new('tastaturlicht.desktop') !== null;

        // Klick auf den Knopf selbst: an/aus
        this.connect('clicked', () => this._anAus());

        // Beim Öffnen des Menüs den aktuellen Zustand holen
        this.menu.connect('open-state-changed', (_menu, offen) => {
            if (offen)
                this.aktualisieren();
        });
        this.aktualisieren();
    }

    aktualisieren() {
        lesen('brightness', text => {
            if (text === null) {
                this.subtitle = 'Treiber fehlt';
                this.checked = false;
                return;
            }
            const stufe = parseInt(text);
            this._aktuelleStufe = stufe;
            if (stufe > 0)
                this._stufe = stufe;
            this._wirdGesetzt = true;
            this.checked = stufe > 0;
            this._regler.value = stufe / HELLIGKEIT_MAX;
            this._wirdGesetzt = false;
            this.subtitle = stufe > 0 ? `Stufe ${stufe}` : 'Aus';
        });
    }

    _helligkeitSetzen(stufe) {
        this._aktuelleStufe = stufe;
        schreiben('brightness', String(stufe));
        this.checked = stufe > 0;
        this.subtitle = stufe > 0 ? `Stufe ${stufe}` : 'Aus';
    }

    _anAus() {
        // toggleMode hat "checked" schon umgedreht
        this._helligkeitSetzen(this.checked ? this._stufe : 0);
        this._wirdGesetzt = true;
        this._regler.value = this.checked ? this._stufe / HELLIGKEIT_MAX : 0;
        this._wirdGesetzt = false;
    }

    _reglerBewegt() {
        if (this._wirdGesetzt)
            return;
        const stufe = Math.round(this._regler.value * HELLIGKEIT_MAX);
        if (stufe === this._aktuelleStufe)
            return;     // nur schreiben, wenn sich die Stufe wirklich ändert
        if (stufe > 0)
            this._stufe = stufe;
        this._helligkeitSetzen(stufe);
    }

    _farbeSetzen(werte) {
        schreiben('multi_intensity', werte);
        // Erst "brightness" schreiben übernimmt die Farbe (Lektion 8)
        this._helligkeitSetzen(this._stufe);
        this._wirdGesetzt = true;
        this._regler.value = this._stufe / HELLIGKEIT_MAX;
        this._wirdGesetzt = false;
    }
});

const LichtAnzeige = GObject.registerClass(
class LichtAnzeige extends SystemIndicator {
    _init(erweiterung) {
        super._init();
        this.quickSettingsItems.push(new LichtKnopf(erweiterung));
    }
});

export default class TastaturlichtErweiterung extends Extension {
    enable() {
        this._anzeige = new LichtAnzeige(this);
        Main.panel.statusArea.quickSettings.addExternalIndicator(this._anzeige);
    }

    disable() {
        this._anzeige.quickSettingsItems.forEach(knopf => knopf.destroy());
        this._anzeige.destroy();
        this._anzeige = null;
    }
}
