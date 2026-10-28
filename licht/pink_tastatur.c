// pink_tastatur.c – Mein Tastaturlicht-Treiber 💗🌉
//
// Er bleibt geladen und baut eine "Brücke" in /sys:
//   /sys/class/leds/pink_tastatur::kbd_backlight/
//     multi_intensity  -> Farbe, z. B. "50 15 32" (Rot Grün Blau, je 0–50)
//     brightness       -> Helligkeit 0 (aus) bis 4 (ganz hell)
//
// Wer in diese Dateien schreibt, ändert sofort die Tastaturfarbe.

#include <linux/module.h>
#include <linux/init.h>
#include <linux/printk.h>
#include <linux/acpi.h>
#include <linux/slab.h>
#include <linux/dmi.h>
#include <linux/mutex.h>                 // Schloss, damit nur einer gleichzeitig schreibt
#include <linux/platform_device.h>       // ein "Gerät", an dem das Licht hängt
#include <linux/led-class-multicolor.h>  // das Linux-LED-System für bunte Lichter

#define UNIWILL_GUID   "ABBC0F6F-8EA1-11D1-00A0-C90629100000"
#define WMI_METHODE_EC 4
#define EC_SCHREIBEN   0
#define EC_LESEN       1
#define EC_FEHLER      0xfefefefe

#define ZEILE_FEATURES 0x0766
#define ZEILE_STATUS   0x078c   // enthält auch die Helligkeit (Bits 5–7)
#define ZEILE_MODUS    0x0767
#define ZEILE_ROT      0x0769
#define ZEILE_GRUEN    0x076a
#define ZEILE_BLAU     0x076b

#define BIT_RGB_TASTATUR      0x04
#define BIT_NUR_WEISS         0x01
#define BIT_FARBE_UEBERNEHMEN 0x20
#define BIT_HELLIGKEIT_UEBERNEHMEN 0x10

#define FARBE_MAX      50   // pro Farbe 0–50
#define HELLIGKEIT_MAX 4    // Helligkeit 0–4

static const struct dmi_system_id mein_laptop[] = {
	{
		.matches = {
			DMI_MATCH(DMI_BOARD_VENDOR, "MECHREVO"),
			DMI_MATCH(DMI_BOARD_NAME, "X6xR55xK"),
		},
	},
	{ }
};

static DEFINE_MUTEX(ec_schloss);
static struct platform_device *mein_geraet;

// ---------- Mit dem EC reden (wie in Lektion 7) ----------

static int ec_paeckchen(u16 adresse, u8 wert, u8 richtung, u32 *antwort_wert)
{
	u8 paeckchen[40] = { 0 };
	struct acpi_buffer rein = { sizeof(paeckchen), paeckchen };
	struct acpi_buffer raus = { ACPI_ALLOCATE_BUFFER, NULL };
	union acpi_object *antwort;
	acpi_status status;
	int fehler = 0;

	paeckchen[0] = adresse & 0xff;
	paeckchen[1] = (adresse >> 8) & 0xff;
	paeckchen[2] = wert;
	paeckchen[5] = richtung;

	status = wmi_evaluate_method(UNIWILL_GUID, 0, WMI_METHODE_EC, &rein, &raus);
	if (ACPI_FAILURE(status))
		return -EIO;

	antwort = raus.pointer;
	if (!antwort || antwort->type != ACPI_TYPE_BUFFER || antwort->buffer.length < 4) {
		fehler = -EIO;
		goto aufraeumen;
	}

	memcpy(antwort_wert, antwort->buffer.pointer, sizeof(*antwort_wert));
	if (*antwort_wert == EC_FEHLER)
		fehler = -EIO;

aufraeumen:
	kfree(raus.pointer);
	return fehler;
}

static int ec_lesen(u16 adresse, u8 *wert)
{
	u32 antwort;
	int fehler = ec_paeckchen(adresse, 0, EC_LESEN, &antwort);

	if (!fehler)
		*wert = antwort & 0xff;
	return fehler;
}

static int ec_schreiben(u16 adresse, u8 wert)
{
	u32 antwort;

	return ec_paeckchen(adresse, wert, EC_SCHREIBEN, &antwort);
}

// ---------- Farbe und Helligkeit ----------

static int farbe_schreiben(u8 rot, u8 gruen, u8 blau)
{
	u8 modus;
	int fehler;

	fehler = ec_schreiben(ZEILE_ROT, rot);
	if (!fehler)
		fehler = ec_schreiben(ZEILE_GRUEN, gruen);
	if (!fehler)
		fehler = ec_schreiben(ZEILE_BLAU, blau);
	if (!fehler)
		fehler = ec_lesen(ZEILE_MODUS, &modus);
	if (!fehler)
		fehler = ec_schreiben(ZEILE_MODUS, modus | BIT_FARBE_UEBERNEHMEN);
	return fehler;
}

static int helligkeit_schreiben(u8 helligkeit)
{
	u8 status;
	int fehler = ec_lesen(ZEILE_STATUS, &status);

	if (fehler)
		return fehler;
	status &= 0x0f;                       // untere 4 Bits behalten
	status |= helligkeit << 5;            // Helligkeit in Bits 5–7
	status |= BIT_HELLIGKEIT_UEBERNEHMEN; // "übernehmen"-Knopf
	return ec_schreiben(ZEILE_STATUS, status);
}

static u8 begrenzen(unsigned int wert)
{
	return wert > FARBE_MAX ? FARBE_MAX : wert;
}

// Wird von Linux aufgerufen, wenn jemand in brightness oder multi_intensity schreibt
static int licht_setzen(struct led_classdev *led, enum led_brightness helligkeit)
{
	struct led_classdev_mc *mc = lcdev_to_mccdev(led);
	u8 rot = begrenzen(mc->subled_info[0].intensity);
	u8 gruen = begrenzen(mc->subled_info[1].intensity);
	u8 blau = begrenzen(mc->subled_info[2].intensity);
	int fehler = 0;

	mutex_lock(&ec_schloss);

	// Alle Farben 0 ist ein Sonderfall im EC -> dann einfach nur die Farbe nicht ändern
	if (rot || gruen || blau)
		fehler = farbe_schreiben(rot, gruen, blau);
	if (!fehler)
		fehler = helligkeit_schreiben(helligkeit);

	mutex_unlock(&ec_schloss);

	if (fehler)
		pr_err("pink_tastatur: Licht setzen hat nicht geklappt (%d)\n", fehler);
	return fehler;
}

// Wird aufgerufen, wenn jemand brightness liest
static enum led_brightness licht_lesen(struct led_classdev *led)
{
	u8 status = 0;

	mutex_lock(&ec_schloss);
	ec_lesen(ZEILE_STATUS, &status);
	mutex_unlock(&ec_schloss);

	return status >> 5;
}

// Die drei Farb-Kanäle: Rot, Grün, Blau
static struct mc_subled farben[3] = {
	{ .color_index = LED_COLOR_ID_RED },
	{ .color_index = LED_COLOR_ID_GREEN },
	{ .color_index = LED_COLOR_ID_BLUE },
};

static struct led_classdev_mc tastatur_licht = {
	.led_cdev = {
		.name = "pink_tastatur::kbd_backlight",
		.max_brightness = HELLIGKEIT_MAX,
		.brightness_set_blocking = licht_setzen,
		.brightness_get = licht_lesen,
		// SUSPENDRESUME: nach dem Aufwachen Licht wiederherstellen
		// RETAIN_AT_SHUTDOWN: beim Entfernen des Treibers das Licht NICHT ausschalten
		.flags = LED_CORE_SUSPENDRESUME | LED_RETAIN_AT_SHUTDOWN,
	},
	.num_colors = 3,
	.subled_info = farben,
};

// ---------- Laden und Entfernen ----------

static int __init pink_start(void)
{
	u8 features, status, r, g, b;
	int fehler;

	if (!dmi_check_system(mein_laptop)) {
		pr_err("pink_tastatur: Das ist nicht mein MECHREVO X6xR55xK!\n");
		return -ENODEV;
	}
	if (!wmi_has_guid(UNIWILL_GUID)) {
		pr_err("pink_tastatur: Keine Uniwill-Tuer gefunden!\n");
		return -ENODEV;
	}

	// RGB-Tastatur? Und aktuelle Werte holen
	if (ec_lesen(ZEILE_FEATURES, &features) || ec_lesen(ZEILE_STATUS, &status) ||
	    ec_lesen(ZEILE_ROT, &r) || ec_lesen(ZEILE_GRUEN, &g) || ec_lesen(ZEILE_BLAU, &b))
		return -EIO;
	if (!(features & BIT_RGB_TASTATUR) || (status & BIT_NUR_WEISS)) {
		pr_err("pink_tastatur: Keine RGB-Tastatur erkannt!\n");
		return -ENODEV;
	}
	if (r > FARBE_MAX || g > FARBE_MAX || b > FARBE_MAX) {
		pr_err("pink_tastatur: Komische Farbwerte im EC - ich mache nichts!\n");
		return -EIO;
	}

	// Mit dem aktuellen Zustand starten
	farben[0].intensity = r;
	farben[1].intensity = g;
	farben[2].intensity = b;
	tastatur_licht.led_cdev.brightness = status >> 5;

	// Ein Gerät anlegen, an dem unser Licht hängt
	mein_geraet = platform_device_register_simple("pink_tastatur", PLATFORM_DEVID_NONE, NULL, 0);
	if (IS_ERR(mein_geraet))
		return PTR_ERR(mein_geraet);

	// Das Licht beim LED-System anmelden -> die Dateien in /sys entstehen
	fehler = led_classdev_multicolor_register(&mein_geraet->dev, &tastatur_licht);
	if (fehler) {
		platform_device_unregister(mein_geraet);
		return fehler;
	}

	pr_info("pink_tastatur: Bereit 💗 Farbe=%u %u %u Helligkeit=%u\n", r, g, b, status >> 5);
	return 0;
}

static void __exit pink_ende(void)
{
	led_classdev_multicolor_unregister(&tastatur_licht);
	platform_device_unregister(mein_geraet);
	pr_info("pink_tastatur: Tschuess 👋 (die Farbe bleibt)\n");
}

module_init(pink_start);
module_exit(pink_ende);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("nes");
MODULE_DESCRIPTION("Tastaturlicht fuer MECHREVO Jiaolong ueber das Linux-LED-System");
