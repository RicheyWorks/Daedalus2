# Gardenkeeper R9

An existing imported Orr Sign Board is now an intentional gardenkeeper kiosk beside
the arrival approach. Within2.4m, the existing non-consuming E interaction opens
or closes the existing garden panel. Walking away closes the temporary message.
The kiosk reads the current garden stage:

- Seed available: "Welcome! Take a seed from the teal stand."
- Seed carried: "Your seed is ready. Plant it in the pink pot."
- Flower planted: "Thank you! Your flower brightens the Commons."

Existing pause/settings/field/dialogue refusals remain. Garden save failures and
unavailable saved state keep their existing error UI; the kiosk does not mask
them. KeeperOpen is temporary, not a new saved stage. The kiosk branch returns
before planting actions and never calls CommitGardenStage, grants a reward or
resets existing progress. InitGarden, CommitGardenStage and SG_CommonsGarden
version1 were retained unchanged. No chart/input-mapping/shared-inventory edits.

Changed only the owned activity Blueprint, owned garden widget and owned map.
One 19px message row was added to the existing420x180panel; title, message and
essential E prompt have separate roles. The kiosk has one primary world label,
not a paragraph of floating instructions. The imported static board avoids a
character rigging/import/animation detour. It is not an animated NPC or dialogue
framework. Exact geometry, build status and preservation are in build.json.

Native Blueprint/UMG compilation and exact saves completed. No Play, repeated
input/persistence proof or reload loop ran in this build-only pass. Runtime
conversation/input/layout remains unverified. The saved editor screenshot shows
the kiosk composition, not a runtime HUD. Existing R7 persistence limits remain.

No next ingestion batch was clearly selected in the current Commons manifests:
they bind only the three pond plants already imported/admitted/placed. Wider
backlog selection remains open; no bulk import was started. Next production
priority is clearer continuous ground/route presentation with current content,
keeping the spacious collision-safe layout and current interaction/progress.
