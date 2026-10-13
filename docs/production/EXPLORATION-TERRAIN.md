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
