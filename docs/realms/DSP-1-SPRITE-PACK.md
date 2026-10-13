# DSP 1: the 8-bit realm's sprite pack

How Sol's Blender art for the portal realm (ADR-052) reaches the screen. The realm renders to a 256x240 software
framebuffer (DaedalusRealmCore.h), so art arrives as pixel sprites in a text pack, not as meshes.

## The contract (Sol -> unreal-team)
1. Render each character/monster from Blender to PNG sprite frames, square, side <= 128 px, frames laid side by side
   in one PNG (frame width = height), alpha < 128 = transparent. Pixel-art sized: monsters 48-64 px, people 16-24 px.
2. Name the files by id:
   - monsters: `BLIGHT_SLIME.png` (2 frames: idle, bob); tiers `BLIGHT_SLIME.2.png`, `BLIGHT_SLIME.3.png`
   - party members: `MEMBER.HERO.png`, `MEMBER.SAGE.png`, `MEMBER.SCOUT.png`, `MEMBER.DRAKE.png` (8 frames: down0 down1 up0 up1 left0 left1 right0 right1).
     DRAKE is the dragon that hatches from the land's DRAGON EGG (ADR-065) and walks fourth in the train; a small green drake, 16-24 px.
   - NPC roles: `NPC.TALK.png`, `NPC.NEWS.png`, `NPC.INN.png`, `NPC.SHOP.png`, `NPC.QUEEN.png` (8 frames)
3. `python tools/realm/sprites.py pack <dir> engines/unreal/DaedalusLink/Content/Realm/realm-7.dsp`
   quantizes to one palette of up to 62 colours and writes the pack; `check` parses it back.
4. Ship the .dsp beside the realm spec. The game loads it at EnterRealm; an id that is missing falls back to the
   realm's drawn shape, so partial packs are fine.

## The format
```
DSP 1
palette <n> <RRGGBB>...        n <= 62; colour i is digit i of 0-9A-Za-z
sprite <id> <w> <h> <frames>   then frames*h rows of w digits, '.' transparent
```
Limits: 4096 sprites, 128x128, 16 frames, lines <= 1024 bytes. Refusals are "line N: why" and identical in
Python (tools/realm/sprites.py) and C++ (DaedalusRealmSprites.h); core-test/realm_sprites_test.cpp replays
tools/realm/sprites_parity.txt.

## Where it is drawn
- Battle: the monster's sprite centred in its 64x64 slot, feet on the slot's bottom; rarity picks `:2`/`:3` first.
- Field: party members and NPCs, feet on the tile's bottom edge, centred; frame by facing and step.
- Hurt flash paints the sprite white, as the drawn shapes do.
