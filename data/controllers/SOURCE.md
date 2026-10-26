# Vendored: SDL_GameControllerDB

`gamecontrollerdb.txt` is the community controller database from https://github.com/mdqinc/SDL_GameControllerDB
(commit c1d5289, 2026-10-02), zlib license (`LICENSE-SDL_GameControllerDB.txt`). It maps thousands of pads,
retro controllers, adapters and arcade sticks to one standard layout per platform. GLFW and SDL read this file
format directly. `tools/controllers/build_bundle.py` merges it with `curated.json` (Daedalus' own lineup notes)
into `controller-bundle.json` for the shared controller module.

To refresh: replace `gamecontrollerdb.txt` with a newer copy, update the commit above, run the builder.
