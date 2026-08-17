# ADR-015: Randomized-weight Kruskal texture — declined

**Status:** Decided — **declined**
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Resolves:** CLRS hit-list G4 remaining half ("randomized-weight Kruskal
texture"). The braiding half shipped 2026-07-18 as `Braider`.

## Question

G4 asked for a Kruskal variant that sorts a randomly weighted edge list for
"a free family of textures", then re-admits rejected edges as a braid factor.
Braiding is done. Is the texture half still a generator?

## Decision

**Decline.** Two facts already in the tree make the remaining half either
already shipped or a duplicate of `WeightedPrimsGenerator`.

1. **Random unique weights are a shuffle.** Kruskal with i.i.d. continuous
   weights produces a uniformly random spanning tree. `KruskalsGenerator`
   already shuffles the edge list. That *is* randomized-weight Kruskal.
   The G1 lesson applies verbatim: an MST depends only on the relative
   order of the weights, so changing the weight *distribution* does not
   change the family of mazes.

2. **Directional bias is already Prim's.** The thing that actually changes
   texture is breaking isotropy (`horizontalBias` on east-west walls).
   `WeightedPrimsGenerator` ships that knob. Kruskal and Prim produce the
   **same** MST for a given unique weight assignment, so a biased Kruskal
   with the same weights is the same maze under a different algorithm
   name. A second id would be a roster lie.

Re-admitting rejected edges is `Braider`, composable with every generator,
which is more general than hanging a braid factor off Kruskal alone.

## Re-fire

A Kruskal that is *not* an MST — for example a texture that depends on
union order beyond the weight permutation — would be a new algorithm and
needs its own name. Until then G4 is closed.
