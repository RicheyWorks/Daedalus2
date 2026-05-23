# Daedalus Algorithm Catalog — Visual & Complexity Guide

## Generator Characteristics

| Algorithm              | Visual Texture              | Bias                  | Complexity     | Best For                  |
|------------------------|-----------------------------|-----------------------|----------------|---------------------------|
| Recursive Backtracker  | Long winding rivers         | Strong DFS bias       | O(n)           | Natural cave-like mazes   |
| Prims                  | Bushy, many dead ends       | Random frontier       | O(n log n)     | Dense, organic feel       |
| Kruskals               | Very uniform, short branches| Unbiased              | O(n α(n))      | Fair, balanced mazes      |
| Borůvka's              | Parallel component growth   | Ultra-uniform         | O(n log n)     | Mathematically clean      |
| Hilbert Curve          | Self-similar fractal swirls | Locality preserving   | O(n)           | Beautiful mathematical art|
| Morton Curve           | Nested Z-quadrant blocks    | Z-order locality      | O(n log n)     | Recursive quadrant look   |
| Archimedes Spiral      | Concentric flowing corridors| Spiral bias           | O(n)           | Elegant, ancient math     |
| Kraken (Eden Growth)   | Chaotic coral / tentacles   | Surface attachment    | O(n)           | Wild, organic branching   |
| Gauss (Quadratic)      | Crystalline, balanced       | r² + c² norm          | O(n log n)     | Mathematically perfect    |
| Turing (State Machine) | Chaotic emergent patterns   | 4-state machine       | O(n)           | Complex, unpredictable    |
| Lightning              | Fast + elegant branching    | Quadratic bias        | O(n)           | Speed + beauty            |
| Wilson's               | Truly unbiased              | Uniform spanning tree | Expected O(n)  | Mathematically perfect    |
| Aldous-Broder          | Unbiased (dual to Wilson)   | Random walk           | Expected O(n²) | Theoretical purity        |

## Solver Characteristics

| Solver     | Optimality     | Speed     | Memory    | Best Use Case             |
|------------|----------------|-----------|-----------|---------------------------|
| A*         | Optimal (with consistent heuristic) | Fast     | Medium    | Most practical cases      |
| Dijkstra   | Optimal        | Medium    | Medium    | Weighted graphs           |
| BFS        | Optimal (unweighted) | Very Fast | Low       | Shortest path in steps    |
| DFS        | Not optimal    | Fast      | Low       | Any path (not shortest)   |

**Recommended Default:** A* with Manhattan heuristic for mazes, A* with region-based heuristic for server routing.

---

*Generated as part of Daedalus v1.6 — Path to 10/10*