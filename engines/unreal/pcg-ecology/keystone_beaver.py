# SPDX-License-Identifier: MIT
"""Chapter 9 'Keystone Beaver': each dam floods the stream cells within r of it (wetland = Island.water, stage reset to 0).
A few dams add a wetland habitat and raise mosaic H; many dams drown the old-growth (stage 3) cells. Goal: H >= target with oaks kept."""
from quest_hook import build_island
def flood(I, dams, r=1):
    for cx, cy in dams:
        cells = [(i, j) for i in range(cx - r, cx + r + 1) for j in range(cy - r, cy + r + 1) if 0 <= i < I.n and 0 <= j < I.n]
        I.dig(cells)
        for i, j in cells: I.t[j][i] = 0.0
    return I
def outcome(dams, r=1):
    I = flood(build_island(), dams, r); st = I.stages()
    return {"H": I.shannon(), "old_growth": st[3], "wetland": len(I.water)}
STREAM = [(i, 6) for i in range(12)]   # stream row through the island (W2 runs west->east through the centre)
def best_dams(k):
    """k dams spread evenly along the stream."""
    return [STREAM[int((n + 0.5) * len(STREAM) / k)] for n in range(k)] if k else []
if __name__ == "__main__":
    for k in range(0, 9): print(k, outcome(best_dams(k)))
