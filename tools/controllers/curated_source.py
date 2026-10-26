# SPDX-License-Identifier: MIT
"""The Daedalus controller lineup, written out as data/controllers/curated.json by build_bundle.py.

Each model: maker, model, kind, family, era, match (case-insensitive regex tried against the browser's pad id and
SDL_GameControllerDB names), optional vid/pid (hex, only where the USB ids are well known), modes, note.
family picks prompt labels and the confirm convention; kind says what the hardware is. USB ids not listed here are
taken from the community database by name match, and the builder reports which models it could not find there.
"""

FAMILIES = {
    # positional names: south / east / west / north face buttons, then shoulders, triggers, back, start
    "xbox":        {"south": "A", "east": "B", "west": "X", "north": "Y", "l": "LB", "r": "RB", "zl": "LT", "zr": "RT", "back": "View", "start": "Menu", "confirm": "south"},
    "playstation": {"south": "Cross", "east": "Circle", "west": "Square", "north": "Triangle", "l": "L1", "r": "R1", "zl": "L2", "zr": "R2", "back": "Create", "start": "Options", "confirm": "south"},
    "nintendo":    {"south": "B", "east": "A", "west": "Y", "north": "X", "l": "L", "r": "R", "zl": "ZL", "zr": "ZR", "back": "-", "start": "+", "confirm": "east"},
    "n64":         {"south": "A", "east": "B", "west": "C-Left", "north": "C-Up", "l": "L", "r": "R", "zl": "Z", "zr": "Z", "back": "C-Down", "start": "Start", "confirm": "south"},
    "gamecube":    {"south": "A", "east": "X", "west": "B", "north": "Y", "l": "L", "r": "R", "zl": "L", "zr": "Z", "back": "Z", "start": "Start", "confirm": "south"},
    "snes":        {"south": "B", "east": "A", "west": "Y", "north": "X", "l": "L", "r": "R", "zl": "L", "zr": "R", "back": "Select", "start": "Start", "confirm": "east"},
    "nes":         {"south": "B", "east": "A", "west": "B", "north": "A", "l": "", "r": "", "zl": "", "zr": "", "back": "Select", "start": "Start", "confirm": "east"},
    "sega":        {"south": "B", "east": "C", "west": "A", "north": "Y", "l": "X", "r": "Z", "zl": "L", "zr": "R", "back": "Mode", "start": "Start", "confirm": "south"},
    "saturn":      {"south": "B", "east": "C", "west": "A", "north": "Y", "l": "L", "r": "R", "zl": "X", "zr": "Z", "back": "", "start": "Start", "confirm": "south"},
    "atari":       {"south": "Fire", "east": "Fire 2", "west": "", "north": "", "l": "", "r": "", "zl": "", "zr": "", "back": "Select", "start": "Menu", "confirm": "south"},
    "arcade":      {"south": "K1", "east": "K2", "west": "P1", "north": "P2", "l": "P3", "r": "K3", "zl": "P4", "zr": "K4", "back": "Select", "start": "Start", "confirm": "south"},
    "neogeo":      {"south": "A", "east": "B", "west": "C", "north": "D", "l": "", "r": "", "zl": "", "zr": "", "back": "Select", "start": "Start", "confirm": "south"},
    "pcengine":    {"south": "II", "east": "I", "west": "", "north": "", "l": "", "r": "", "zl": "", "zr": "", "back": "Select", "start": "Run", "confirm": "east"},
    "generic":     {"south": "1", "east": "2", "west": "3", "north": "4", "l": "L1", "r": "R1", "zl": "L2", "zr": "R2", "back": "Select", "start": "Start", "confirm": "south"},
}

M = []
def add(maker, model, kind, family, era, match, vid=None, pid=None, modes=None, note=""):
    M.append({k: v for k, v in dict(maker=maker, model=model, kind=kind, family=family, era=era, match=match,
                                     vid=vid, pid=pid, modes=modes or [], note=note).items() if v not in (None, "", [])})

# ---- Microsoft --------------------------------------------------------------------------------------------
add("Microsoft", "Xbox 360 Controller", "pad", "xbox", "2005", r"xbox 360|x-?input", "045e", "028e", ["xinput"])
add("Microsoft", "Xbox One Controller", "pad", "xbox", "2013", r"xbox one(?! elite)", "045e", "02ea", ["xinput", "bluetooth"])
add("Microsoft", "Xbox Elite Controller", "pad", "xbox", "2015", r"elite controller(?! series)|xbox one elite(?! 2)", "045e", "02e3", ["xinput"])
add("Microsoft", "Xbox Elite Series 2", "pad", "xbox", "2019", r"elite.*(series )?2|0b00|0b05|0b22", "045e", "0b00", ["xinput", "bluetooth"],
    "Back paddles are mapped in Xbox Accessories to face buttons, so they arrive as those buttons.")
add("Microsoft", "Xbox Series X|S Controller", "pad", "xbox", "2020", r"xbox series|xbox wireless controller", "045e", "0b12", ["xinput", "bluetooth"])
add("Microsoft", "Xbox Adaptive Controller", "pad", "xbox", "2018", r"adaptive", "045e", "0b0a", ["xinput"], "Its 3.5 mm jacks map to buttons in Xbox Accessories.")
# ---- Sony -------------------------------------------------------------------------------------------------
add("Sony", "DualShock 3", "pad", "playstation", "2007", r"ps3|playstation\(r\)3|sixaxis", "054c", "0268")
add("Sony", "DualShock 4", "pad", "playstation", "2013", r"ps4|dualshock 4|wireless controller", "054c", "05c4")
add("Sony", "DualSense", "pad", "playstation", "2020", r"dualsense|ps5 controller", "054c", "0ce6")
add("Sony", "DualSense Edge", "pad", "playstation", "2023", r"dualsense edge", "054c", "0df2")
add("Sony", "PlayStation Classic Controller", "retro", "playstation", "2018", r"playstation classic", "054c", "0cda")
add("Sony", "Access Controller", "pad", "playstation", "2023", r"access controller")
# ---- Nintendo ---------------------------------------------------------------------------------------------
add("Nintendo", "Switch Pro Controller", "pad", "nintendo", "2017", r"switch pro|^pro controller|057e.{0,12}2009", "057e", "2009", ["usb", "bluetooth"])
add("Nintendo", "Joy-Con (L/R)", "pad", "nintendo", "2017", r"joy-?con", "057e", "2006", ["bluetooth"], "A single sideways Joy-Con has four face buttons and a stick.")
add("Nintendo", "Switch 2 Pro Controller", "pad", "nintendo", "2025", r"switch 2 pro|pro controller 2")
add("Nintendo", "NES Controller (Switch Online)", "retro", "nes", "2018", r"nso nes|nes controller \(switch|famicom controller")
add("Nintendo", "SNES Controller (Switch Online)", "retro", "snes", "2019", r"nso snes|snes controller", "057e", "2017")
add("Nintendo", "N64 Controller (Switch Online)", "retro", "n64", "2021", r"nso n64|n64 controller", "057e", "2019")
add("Nintendo", "Sega Genesis Controller (Switch Online)", "retro", "sega", "2021", r"nso sega genesis|nso mega drive", "057e", "201e")
add("Nintendo", "GameCube Controller Adapter (WUP-028)", "adapter", "gamecube", "2014", r"wup-028|gamecube adapter|gc adapter", "057e", "0337",
    note="Four GameCube pads on one USB plug; each appears as its own pad.")
add("Nintendo", "Wii U Pro Controller", "pad", "nintendo", "2012", r"wii u pro", "057e", "0330")
add("Nintendo", "Wii Classic Controller (via adapter)", "adapter", "snes", "2006", r"wii classic")
# ---- Razer ------------------------------------------------------------------------------------------------
for model, era, note in [
    ("Wolverine V3 Pro", "2024", "8000 Hz PC polling (HyperPolling dongle). The browser samples about 250 Hz; native builds see full rate."),
    ("Wolverine V3 Tournament Edition", "2024", "8000 Hz wired polling. Four remappable back buttons arrive as whatever Synapse assigns."),
    ("Wolverine V3 Pro 8K PC", "2025", "8K PC edition; remappable buttons arrive as their Synapse assignment."),
    ("Wolverine V2 Pro", "2022", "Xbox and PlayStation editions (the PS5 edition reports as a DualSense-style pad)."),
    ("Wolverine V2 Chroma", "2021", ""), ("Wolverine V2", "2020", ""),
    ("Wolverine Ultimate", "2018", ""), ("Wolverine Tournament Edition", "2018", ""),
]:
    add("Razer", model, "pad", "xbox", era, "wolverine" + (r".*v3" if "V3" in model else r".*v2" if "V2" in model else r"(?!.*v[23])"), "1532", modes=["xinput"], note=note)
add("Razer", "Wolverine V2 Pro (PS5)", "pad", "playstation", "2022", r"wolverine ps5|wolverine v2 pro.*ps", "1532")
add("Razer", "Raiju (Tournament / Ultimate / Mobile)", "pad", "playstation", "2017", r"raiju", "1532")
add("Razer", "Kishi / Kishi V2 / Kishi V2 Pro", "mobile", "xbox", "2020", r"kishi(?! ultra)", "1532", modes=["usb-c", "lightning"])
add("Razer", "Kishi Ultra", "mobile", "xbox", "2024", r"kishi ultra", "1532", modes=["usb-c"])
add("Razer", "Kitsune (leverless)", "arcade", "arcade", "2023", r"kitsune", "1532", note="All-button layout; directions arrive as the d-pad.")
add("Razer", "Panthera Evo", "arcade", "arcade", "2018", r"panthera", "1532")
add("Razer", "Atrox", "arcade", "arcade", "2015", r"atrox", "1532", modes=["xinput"])
add("Razer", "Onza", "pad", "xbox", "2011", r"onza", "1532")
add("Razer", "Sabertooth", "pad", "xbox", "2013", r"sabertooth", "1532")
add("Razer", "Serval", "mobile", "xbox", "2015", r"serval", "1532")
# ---- GameSir ----------------------------------------------------------------------------------------------
for model, era, kind in [
    ("G7 Pro", "2025", "pad"), ("G7 HE", "2024", "pad"), ("G7 SE", "2023", "pad"), ("G7", "2022", "pad"),
    ("Cyclone 2", "2024", "pad"), ("Kaleid Flux", "2024", "pad"), ("Super Nova", "2024", "pad"), ("Nova", "2023", "pad"), ("Nova Lite", "2023", "pad"),
    ("T4 Kaleid", "2023", "pad"), ("T4 Cyclone Pro", "2023", "pad"), ("T4 Cyclone", "2023", "pad"), ("T4 Pro", "2020", "pad"), ("T4 Mini", "2021", "pad"),
    ("Tarantula Pro", "2025", "pad"), ("T7", "2023", "pad"), ("G8 Galileo", "2023", "mobile"), ("G8 Plus", "2024", "mobile"),
    ("X2 Pro", "2022", "mobile"), ("X2s", "2023", "mobile"), ("X3 Type-C", "2022", "mobile"), ("X4 Aileron", "2023", "mobile"), ("X5 Lite", "2024", "mobile"),
    ("G4 Pro", "2019", "pad"), ("G4s", "2018", "pad"), ("G3", "2017", "pad"), ("G5", "2019", "mobile"),
]:
    rx = r"gamesir[ -]?" + model.lower().replace(" ", r"[ -]?").replace("plus", r"(\+|plus)")
    add("GameSir", model, kind, "xbox", era, rx, "3537", modes=["xinput", "switch", "android", "ios"],
        note="Switch mode reports as a Nintendo pad (A on the right); Android/iOS modes may need BIND.")
# ---- 8BitDo ------------------------------------------------------------------------------------------------
for model, fam, era, kind in [
    ("Ultimate 2 Wireless", "xbox", "2024", "pad"), ("Ultimate 2C", "xbox", "2023", "pad"), ("Ultimate", "xbox", "2021", "pad"),
    ("Pro 3", "nintendo", "2025", "pad"), ("Pro 2", "nintendo", "2020", "pad"), ("SN30 Pro+", "nintendo", "2019", "pad"), ("SN30 Pro", "snes", "2018", "pad"),
    ("SN30", "snes", "2018", "retro"), ("SF30", "snes", "2016", "retro"), ("N30", "nes", "2018", "retro"), ("NES30 Pro", "nes", "2016", "retro"),
    ("M30", "sega", "2019", "retro"), ("64 Controller", "n64", "2025", "retro"), ("Lite 2", "nintendo", "2021", "pad"), ("Lite SE", "nintendo", "2022", "pad"),
    ("Zero 2", "snes", "2019", "retro"), ("Micro", "snes", "2022", "retro"), ("Arcade Stick", "arcade", "2020", "arcade"), ("NEOGEO Controller", "neogeo", "2023", "retro"),
    ("Retro Receiver", "generic", "2018", "adapter"),
]:
    rx = r"8bitdo[ -]?" + model.lower().replace("+", r"\+").replace(" ", r"[ -]?")
    add("8BitDo", model, kind, fam, era, rx, "2dc8", modes=["xinput", "switch", "dinput", "macos"], note="Mode switch changes how it reports; X-input mode is the most reliable.")
# ---- Hori, PowerA, PDP, others (modern) -------------------------------------------------------------------
for maker, model, kind, fam, era, rx, vid in [
    ("Hori", "Fighting Stick Alpha", "arcade", "arcade", "2020", r"fighting stick (alpha|α)", "0f0d"),
    ("Hori", "Real Arcade Pro", "arcade", "arcade", "2010", r"real arcade pro|rap ", "0f0d"),
    ("Hori", "Fighting Commander", "pad", "arcade", "2014", r"fighting commander", "0f0d"),
    ("Hori", "Fighting Stick Mini", "arcade", "arcade", "2017", r"fighting stick mini", "0f0d"),
    ("Hori", "HORIPAD (Switch / PS / Xbox)", "pad", "xbox", "2017", r"horipad|hori pad", "0f0d"),
    ("Hori", "Split Pad Pro", "pad", "nintendo", "2019", r"split pad", "0f0d"),
    ("Hori", "Battle Pad (GameCube style)", "pad", "gamecube", "2018", r"battle pad", "0f0d"),
    ("Hori", "Nintendo 64 Controller for Switch", "retro", "n64", "2023", r"hori.*64|horipad.*n64", "0f0d"),
    ("Hori", "PC Engine Mini Controller", "retro", "pcengine", "2020", r"pc engine", "0f0d"),
    ("PowerA", "Enhanced / Fusion / Spectra pads", "pad", "xbox", "2018", r"powera|power a", "20d6"),
    ("PDP", "Afterglow / Rock Candy / Victrix", "pad", "xbox", "2015", r"afterglow|rock candy|pdp", "0e6f"),
    ("Turtle Beach", "Recon / Stealth Ultra", "pad", "xbox", "2022", r"recon controller|stealth ultra|turtle beach", None),
    ("Logitech", "F310", "pad", "xbox", "2010", r"f310", "046d"),
    ("Logitech", "F710", "pad", "xbox", "2010", r"f710", "046d"),
    ("Nacon", "Revolution / Daija", "pad", "playstation", "2016", r"nacon|revolution|daija", "146b"),
    ("Thrustmaster", "eSwap", "pad", "xbox", "2020", r"eswap|thrustmaster", "044f"),
    ("SCUF", "Instinct / Reflex", "pad", "xbox", "2021", r"scuf", None),
    ("Flydigi", "Vader / Apex / Direwolf", "pad", "xbox", "2022", r"flydigi|vader|apex 4|direwolf", None),
    ("Valve", "Steam Controller", "pad", "xbox", "2015", r"steam controller", "28de"),
    ("Valve", "Steam Deck", "pad", "xbox", "2022", r"steam deck", "28de"),
    ("Google", "Stadia Controller", "pad", "xbox", "2019", r"stadia", "18d1"),
    ("Amazon", "Luna Controller", "pad", "xbox", "2020", r"luna", "1949"),
    ("Backbone", "Backbone One", "mobile", "xbox", "2020", r"backbone", None),
    ("Mad Catz", "TE2+ / Ego / FightPad", "arcade", "arcade", "2015", r"mad catz|madcatz|te2|tournament edition 2", "0738"),
]:
    add(maker, model, kind, fam, era, rx, vid)
# ---- Sega ----------------------------------------------------------------------------------------------------
add("Sega", "Mega Drive / Genesis Mini 6-button", "retro", "sega", "2019", r"mega drive mini 6b|genesis mini 6|mega drive mini 2", "0ca3", "0024")
add("Sega", "Genesis Mini 3-button", "retro", "sega", "2019", r"genesis mini 3b|mega drive mini 3b|mega drive controller", "0ca3")
add("Sega", "Astro City Mini arcade stick", "arcade", "arcade", "2021", r"astro city", "0ca3")
add("Retro-bit", "Sega Genesis 6-button USB (licensed)", "retro", "sega", "2018", r"retro bit sega genesis|retro-?bit.*genesis|mega drive$")
add("Retro-bit", "Sega Saturn USB / 2.4 GHz (licensed)", "retro", "saturn", "2019", r"retro bit saturn|retro-?bit.*saturn|sega saturn")
add("Retrolink", "Sega Saturn Classic USB", "retro", "saturn", "2014", r"retrolink.*saturn")
add("Mayflash", "Saturn / Dreamcast adapters", "adapter", "saturn", "2016", r"mayflash saturn|dreamcast")
add("Raphnet", "Saturn / Dreamcast / Jaguar / 3DO / N64 / GC adapters", "adapter", "generic", "2010", r"raphnet",
    note="One adapter, many classic pads; the classic pad's own labels apply.")
# ---- Atari ---------------------------------------------------------------------------------------------------
add("Atari", "CX40+ Joystick (2600+ / 7800+)", "joystick", "atari", "2023", r"cx40|2600\+|7800\+|atari cx controller",
    note="One fire button and a digital stick. One-button rule: tap = confirm, hold = back, hold longer = menu.")
add("Atari", "CX78+ Gamepad", "retro", "atari", "2024", r"cx78")
add("Atari", "CX30+ Paddles", "paddle", "atari", "2024", r"cx30|paddle", note="Each paddle is an analog dial (an axis) with one button.")
add("Atari", "VCS Classic Joystick", "joystick", "atari", "2021", r"atari vcs classic", "3250", "1001", note="Stick twist is an axis; fire plus two face buttons.")
add("Atari", "VCS Modern Controller", "pad", "xbox", "2021", r"atari vcs modern", "3250", "1002")
add("Atari", "Ultimate Atari Fight Stick", "arcade", "arcade", "2022", r"ultimate atari fight stick")
add("Atari", "Gamestation Pro (arcade panel)", "arcade", "arcade", "2019", r"gamestation pro")
# ---- Nintendo-era retro (third party) ----------------------------------------------------------------------
add("Hyperkin", "Admiral N64", "retro", "n64", "2020", r"admiral")
add("Retro-bit", "Tribute64 (N64)", "retro", "n64", "2022", r"tribute ?64")
add("Mayflash", "N64 / GameCube / NES-SNES adapters", "adapter", "n64", "2014", r"mayflash (n64|gamecube|gc)|n64 adapter|adaptoid|retroport")
add("iBuffalo", "Classic USB Gamepad (SNES style)", "retro", "snes", "2010", r"ibuffalo|buffalo classic|snes ?usb", "0583", "2060")
add("Generic", "USB NES / SNES pads (DragonRise)", "retro", "snes", "2012", r"usb gamepad|0079.{0,12}0011|dragonrise", "0079", "0011")
add("Hyperkin", "Duke / Ranger / Trooper", "pad", "xbox", "2018", r"hyperkin")
add("SNK", "NEOGEO mini PAD / Arcade Stick Pro", "retro", "neogeo", "2018", r"neogeo|neo geo|neo-geo")
# ---- Arcade sticks, hit boxes, encoders ---------------------------------------------------------------------
for maker, model, rx, vid, note in [
    ("Victrix", "Pro FS / Pro FS-12", r"victrix", "0e6f", ""),
    ("Qanba", "Obsidian 2 / Drone 2 / Sapphire", r"qanba", "2c22", ""),
    ("Hit Box", "Hit Box / Smash Box / Cross|Up", r"hit ?box|smash ?box|cross\|up", None, "All-button; directions arrive as the d-pad (SOCD handled by the box)."),
    ("Junkfood", "Snack Box Micro", r"snack ?box", None, "GP2040-CE inside: pick X-input mode."),
    ("GP2040-CE", "Raspberry Pi Pico boards (DIY, many brands)", r"gp2040|pico ?(fight|game)", None, "Firmware can pose as X-input, Switch or PS4; X-input mode is the most reliable."),
    ("Brook", "Universal Fighting Board / converters", r"brook", "0c12", ""),
    ("Mayflash", "F300 / F500 / F700 arcade sticks", r"mayflash f[357]00|f300|f500", "33df", ""),
    ("Zero Delay", "USB encoder (cabinet builds)", r"zero ?delay|0079.{0,12}0006|generic.*usb joystick", "0079", "0006"),
    ("Xin-Mo", "Dual arcade encoder", r"xin-?mo|xinmo", "16c0", "05e1"),
    ("Ultimarc", "I-PAC (keyboard encoder) / UltraStik 360", r"ultimarc|ultrastik|i-?pac", "d209", "I-PAC sends MAME default keys; the module's arcade keyboard map reads them."),
    ("X-Arcade", "Dual / Solo (keyboard mode)", r"x-?arcade", None, "Mode 1 sends MAME default keys."),
    ("Arcade1Up", "Cabinet controls via encoder", r"arcade1up", None, "Reported through the encoder inside (usually a Zero Delay)."),
]:
    add(maker, model, "arcade", "arcade", "", rx, vid if vid and len(vid) == 4 else None,
        "0006" if model.startswith("USB encoder") else "05e1" if maker == "Xin-Mo" else None, note=note)

# MAME default keyboard layout, used by I-PAC / X-Arcade / most cabinet keyboard encoders (KeyboardEvent.code).
MAME_KEYS = {
    "p1": {"dpup": "ArrowUp", "dpdown": "ArrowDown", "dpleft": "ArrowLeft", "dpright": "ArrowRight",
           "b1": "ControlLeft", "b2": "AltLeft", "b3": "Space", "b4": "ShiftLeft", "b5": "KeyZ", "b6": "KeyX",
           "start": "Digit1", "coin": "Digit5"},
    "p2": {"dpup": "KeyR", "dpdown": "KeyF", "dpleft": "KeyD", "dpright": "KeyG",
           "b1": "KeyA", "b2": "KeyS", "b3": "KeyQ", "b4": "KeyW", "start": "Digit2", "coin": "Digit6"},
}
