# Physical exploration terrain

User direction: long stretches of usable land with buffalo, ground vehicles and
crash derbies, airships in the sky and spacecraft in space. Add an all-sea realm
with boats, diving and underwater exploration, using Nintendo Jaws as an adventure
feel reference. Preserve and polish existing content. Original names/art/story.

The new portable geometry core builds indexed metre-scale prairie or seabed
patches. Prairie offers rolling open land and a continuous 16 m wide flat travel
corridor with smooth shoulders. Ocean terrain stays submerged beneath a proposed
water level of zero. Shared world-coordinate heights prevent patch-edge cracks
when adjacent patches use the same grid. This geometry is not yet spawned in Unreal.

Native adapter work: feed vertices and indices into the existing mesh component,
rebase world doubles into patch-local Unreal centimetres, add collision and normals,
then stream patches using established land bounds. Terrain outside ownership bounds
needs an approved public-land policy. This core does not move islands, increase NFT
dimensions, or reserve new token lands. A flat corridor alone is not a navigation mesh.

Existing vehicle seam: ADR-043 documents the live mount/drive/dismount Ghost.
Reuse its interaction conventions for future original cars/boats; physical water
buoyancy, diving controls, drowning/air rules, shark AI, derby damage, airships and
spacecraft are pending. The core does not implement those vehicles.

Ocean story proposal: boat routes link floating harbours above drowned settlements.
Players dive for clues, help stranded crews, discover underwater routes, and return
to safety as dangerous wildlife approaches. Rainbow travel links the sea realm to
the existing realms. Final name, settlements, rewards and survival rules need review.

## Approved dock travel rules

User clarification: docks supply boats and submarines. Boarding from Dragon
Warrior (existing internal Portal Realm key) enters the Ocean Realm. Landing on
its ordinary shore returns to Dragon Warrior. Configured underwater docks can
connect to other worlds. This is an additional travel route alongside rainbows.

DaedalusOceanTravelCore resolves configured dock/arrival pairs and rejects missing
anchors, mismatched departure realms and surface boats at submerged docks. Other
realm destinations require underwater docks. Names use existing Portal Realm and
Gallery City keys; Ocean Realm is a proposed new internal key, pending registration.
Host-authoritative dock lookup, permissions, vehicle possession, save/restore,
streaming handover and arrival collision checks still need native integration.
Pure route resolution does not teleport players or establish cross-server authority.

ADaedalusExplorationTerrain now supplies an additive native actor source using
the existing ProceduralMeshComponent dependency, patch-local centimetres,
generated normals/tangents, assignable material and static terrain collision.
Its UHT/module compile and live placement are not yet verified. Invalid dimensions
return an empty core patch; invalid sample coordinates return NaN rather than
throwing, for Unreal builds that disable C++ exceptions.

Patch normals now sample world-coordinate derivatives, and UVs use world
coordinates, so neighboring patches share shading and texture phase. Patch
dimension overflow refuses generation. MSVC /W4 /WX passes 78,383 checks after
these changes; source-level tests do not establish rendered Unreal appearance.

Native build, October 13: isolated UE 5.8 scratch host compiled this actor and
generated reflection module, then linked UnrealEditor-DaedalusLink.dll in 47.18
seconds. Only this actor/core and a validation module were included; the full
current plugin and live placement remain unverified. Log retained at
Documents/Codex/2026-10-13/terrain-ue-compile/verified-build.log. Supported
NoHotReloadFromIDE/NoLiveCoding settings kept hot reload out of this scratch
build. Unreal turn released in hub message 28738.

Dock-input hardening, October 13: route resolution now rejects vehicle enum
values other than Boat or Submarine instead of treating unknown values as
submarines. All dock IDs, realms and arrival anchors must be nonempty, at most
128 bytes, and contain no ASCII control characters. This includes the departure
anchor. Valid boats retain surface routes, valid submarines retain underwater
dock connections, and ordinary shores still return only to Portal Realm.
MSVC C++17 /W4 /WX passed 59 route checks, including invalid vehicle values,
each malformed dock field and the accepted anchor-length boundary. This proves
the portable resolver; server-owned dock lookup, vehicle possession and live
Unreal transitions remain required before travel is usable by players.
