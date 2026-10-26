# SPDX-License-Identifier: MIT
"""Where each setting sits (a modern console game's tabs and sections) and the rows Unreal doesn't have yet.

Native rows are referenced by id only; their definitions come from DaedalusSettings.cpp. A new row is added
only when something reads it (CONSUMERS). Audio defaults reuse data/settings/defaults.json.
"""
import json
import os

_D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "settings", "defaults.json"), encoding="utf-8"))
_A = _D.get("audio", {})
_G = _D.get("gameplay", {})

RESEARCH = [
]

# Tabs in a modern console game's order; sections in its order; Daedalus-only sections are marked (ours).
TABS = [
    {"id": "CONTROLLER", "sections": [
        {"name": "General", "rows": ["ButtonLayout", "ThumbstickLayout", "Vibration", "VibrationStrength", "ConfirmButton"]},
        {"name": "Movement & Aiming", "rows": ["InvertLookY", "InvertLookX"]},
        {"name": "Sensitivity & Acceleration", "rows": ["LookAccel", "LookSensH", "LookSensV"]},
        {"name": "Trigger Deadzone", "rows": ["TriggerInnerDeadzone", "TriggerOuterDeadzone"]},
        {"name": "Move Thumbstick", "rows": ["LeftDeadzone", "LeftMaxInput", "LeftAxialDeadzone"]},
        {"name": "Look Thumbstick", "rows": ["RightDeadzone", "RightMaxInput", "RightAxialDeadzone"]},
    ]},
    {"id": "KEYBOARD/MOUSE", "sections": [
        {"name": "Movement & Aiming", "rows": ["InvertMouseY"]},
        {"name": "Sensitivity", "rows": ["MouseSensH", "MouseSensV"]},
    ]},
    {"id": "VIDEO", "sections": [
        {"name": "Display", "rows": ["FieldOfView"]},
        {"name": "Camera", "rows": ["CameraView", "Shoulder", "Reticle", "CameraDistance"]},
    ]},
    {"id": "AUDIO", "sections": [
        {"name": "Volume", "rows": ["MainVolume", "VoiceVolume", "MusicVolume", "MenuMusicVolume", "EffectsVolume", "InactiveMute"]},
        {"name": "Hardware", "rows": ["DynamicRange"]},
    ]},
    {"id": "GAMEPLAY", "sections": [
        {"name": "Combat", "rows": ["ShieldMode"]},
        {"name": "Heads-up Display (HUD)", "rows": ["TipsTutorials", "FpsCounter"]},
    ]},
    {"id": "ACCESSIBILITY", "sections": [
        {"name": "Menu Navigation", "rows": ["TextSize", "NotificationDuration"]},
        {"name": "Camera", "rows": ["CameraLag"]},
    ]},
]

def _s(label, help, default, lo, hi, step, unit=""):
    return {"label": label, "help": help, "kind": "slider", "default": float(default), "min": float(lo), "max": float(hi), "step": float(step), "unit": unit, "choices": []}

def _t(label, help, default):
    return {"label": label, "help": help, "kind": "toggle", "default": float(default), "min": 0.0, "max": 1.0, "step": 1.0, "unit": "", "choices": []}

def _c(label, help, default, choices):
    return {"label": label, "help": help, "kind": "choice", "default": float(default), "min": 0.0, "max": float(len(choices) - 1), "step": 1.0, "unit": "", "choices": choices}

NEW = {
    "ConfirmButton": _c("Menu Confirm Button", "Which face button confirms in menus and the RPG realms. By Label follows the pad: Nintendo-style pads confirm with A, which sits on the right. Bottom confirms with the bottom button on every pad.", 0, ["BY LABEL", "BOTTOM"]),
    "TriggerInnerDeadzone": _s("Inner Deadzone", "How far a trigger must travel before it counts. Raise it if a resting trigger fires.", 5, 0, 40, 1, "%"),
    "TriggerOuterDeadzone": _s("Outer Deadzone", "How far a trigger must travel to count as fully pulled. Lower it for short-throw triggers (trigger stops on Elite and Razer pads).", 95, 60, 100, 1, "%"),
    "LeftMaxInput": _s("Max Input Threshold", "How far the move stick must go to count as full speed. Lower it if your stick never quite reaches the edge.", 100, 60, 100, 1, "%"),
    "LeftAxialDeadzone": _s("Axial Deadzone", "Ignores small sideways drift while pushing straight. 0 keeps the stick fully round (radial).", 0, 0, 30, 1, "%"),
    "RightMaxInput": _s("Max Input Threshold", "How far the look stick must go to turn at full rate.", 100, 60, 100, 1, "%"),
    "RightAxialDeadzone": _s("Axial Deadzone", "Ignores small vertical drift while turning sideways, and the reverse. 0 keeps the stick fully round (radial).", 0, 0, 30, 1, "%"),
    "MainVolume": _s("Main", "Everything you hear.", round(_A.get("master", 0.8) * 100), 0, 100, 5, "%"),
    "VoiceVolume": _s("Voice", "Characters, announcers and the realm's voices.", 100, 0, 100, 5, "%"),
    "MusicVolume": _s("Music", "Music while you play: field, town, dungeon and battle themes.", round(_A.get("music", 0.6) * 100), 0, 100, 5, "%"),
    "MenuMusicVolume": _s("Menu Music", "Music on title screens and menus.", round(_A.get("music", 0.6) * 100), 0, 100, 5, "%"),
    "EffectsVolume": _s("Sound Effects", "Swings, hits, menus, doors and every other effect.", round(_A.get("sfx", 0.8) * 100), 0, 100, 5, "%"),
    "InactiveMute": _t("Inactive Mute", "Mute the game while its window or tab is in the background.", 1),
    "DynamicRange": _c("Dynamic Range", "Dynamic keeps loud moments loud. Compressed evens the volume out for late nights and small speakers.", 0, ["DYNAMIC", "COMPRESSED"]),
    "TipsTutorials": _t("Tips & Tutorials", "Show control hints and first-time tips.", 1 if _G.get("show_tutorial", True) else 0),
    "FpsCounter": _t("FPS Counter", "Show frames per second in a corner.", 0),
    "TextSize": _c("Text Size", "Size of menu and settings text.", 0, ["DEFAULT", "LARGE", "EXTRA LARGE"]),
    "NotificationDuration": _s("Notification Duration", "How long pop-up notices stay on screen.", 5, 2, 20, 1, " s"),
}

# Who reads each row. Native rows default to ["unreal"]; listed here when the web clients read them too.
CONSUMERS = {
    "ButtonLayout": ["unreal", "realm"], "ThumbstickLayout": ["unreal", "realm"],
    "Vibration": ["unreal", "web-pad"], "VibrationStrength": ["unreal", "web-pad"],
    "InvertLookY": ["unreal", "realm"], "InvertLookX": ["unreal", "realm"],
    "LookAccel": ["unreal", "realm"], "LookSensH": ["unreal", "realm"], "LookSensV": ["unreal", "realm"],
    "LeftDeadzone": ["unreal", "web-pad"], "RightDeadzone": ["unreal", "web-pad"],
    "MouseSensH": ["unreal", "realm"],
    "FieldOfView": ["unreal", "realm"],
    "TriggerInnerDeadzone": ["web-pad"], "TriggerOuterDeadzone": ["web-pad"],
    "LeftMaxInput": ["web-pad"], "LeftAxialDeadzone": ["web-pad"], "RightMaxInput": ["web-pad"], "RightAxialDeadzone": ["web-pad"],
    "MainVolume": ["demo"], "VoiceVolume": ["demo"], "MusicVolume": ["demo"], "MenuMusicVolume": ["demo"], "EffectsVolume": ["demo"],
    "InactiveMute": ["demo"], "DynamicRange": ["demo"],
    "TipsTutorials": ["realm", "demo"], "ConfirmButton": ["web-pad", "demo", "realm"], "FpsCounter": ["realm"],
    "TextSize": ["settings-panel"], "NotificationDuration": ["realm"],
}
