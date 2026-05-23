// SPDX-License-Identifier: MIT

/**
 * Daedalus API Data Transfer Objects
 * 
 * TypeScript equivalents of the Java DTO records for frontend consumption.
 * Generated based on the provided backend DTOs for /api/* endpoints and STOMP frames.
 * 
 * @see PluginInfo.java, SolveResponse.java, GenerateResponse.java, etc.
 */

// ============================================
// Core Models
// ============================================

/**
 * Grid coordinate used throughout the maze system.
 * Note: In maze contexts, `row` corresponds to Y-axis (top-to-bottom),
 * `col` to X-axis (left-to-right).
 */
export interface Point {
  row: number;
  col: number;
}

/**
 * Plugin manifest — mirror of `com.daedalus.plugin.PluginManifest` (a Java record).
 *
 * What a plugin contributes (generators / solvers / themes / etc.) is NOT a manifest field —
 * it's returned at runtime by `MazePlugin.contributedAlgorithms()` and surfaces in the
 * REST `/api/v1/algorithms` response, not here. The manifest is just identity + dependencies.
 */
export interface PluginManifest {
  /** unique slug, e.g. "biome-generators" */
  id: string;
  /** human-readable display name */
  displayName: string;
  /** semver-ish version string, e.g. "1.0.0" */
  version: string;
  /** plugin author */
  author: string;
  /** longer description / blurb */
  description: string;
  /** ids of other plugins this one depends on (loaded first); empty array if none */
  requires: string[];
}

// ============================================
// REST API DTOs
// ============================================

/**
 * Element of the response body for GET /api/plugins.
 * Lightweight projection of a PluginRegistry.Entry suitable for HTTP clients.
 */
export interface PluginInfo {
  /** plugin id from the manifest */
  id: string;
  /** lifecycle state name (DISCOVERED, INITIALIZED, STARTED, STOPPED, or FAILED) */
  state: 'DISCOVERED' | 'INITIALIZED' | 'STARTED' | 'STOPPED' | 'FAILED' | string;
  /** the plugin's full manifest */
  manifest: PluginManifest;
  /** toString() of the last error, or null if the plugin is healthy */
  error: string | null;
}

/**
 * Request body for POST /api/maze/generate.
 */
export interface GenerateRequest {
  /** identifier of the registered generator algorithm (e.g. "binary-tree") */
  generatorId: string;
  /** number of rows in the maze grid */
  rows: number;
  /** number of columns in the maze grid */
  cols: number;
  /** optional RNG seed; when null the server uses System.nanoTime() */
  seed?: number | null;
}

/**
 * Response body for POST /api/maze/generate and GET /api/maze/{id}.
 *
 * generatorId reflects the actual generator that produced the cached maze, which may
 * differ from the requested id when a circuit-breaker fallback fires.
 */
export interface GenerateResponse {
  /** server-assigned maze id */
  id: string; // UUID as string
  /** id of the algorithm that actually produced this maze */
  generatorId: string;
  /** row count */
  rows: number;
  /** column count */
  cols: number;
  /** seed used to generate the maze. Note: Java emits a long; values past 2^53 will lose
   *  precision in JS Number. Seeds from System.nanoTime() are safe in practice. */
  seed: number;
  /**
   * Row-major tile glyph grid (walls, passages, start, goal).
   *
   * The Java side is `char[][]`, which Jackson's default serializer emits as an array of
   * strings (one string per row), NOT as a 2D array of single-character strings. Each row is
   * already concatenated, e.g. `["##.#.G", "#..#..", ...]`. Index a single tile with
   * `tiles[row].charAt(col)`.
   *
   * If you need `string[][]` instead, register a custom Jackson serializer on the server side.
   */
  tiles: string[];
}

/**
 * Response body for POST /api/maze/{id}/session.
 */
export interface SessionResponse {
  /** server-assigned session id */
  sessionId: string; // UUID
  /** id of the maze the session is bound to */
  mazeId: string; // UUID
  /** initial player position (the maze's start cell) */
  position: Point;
}

/**
 * Request body for POST /api/session/{id}/move.
 */
export interface MoveRequest {
  /** grid coordinate the player wants to move to (must be adjacent to the current position) */
  to: Point;
}

/**
 * Response body for POST /api/maze/{id}/solve/{solverId}.
 */
export interface SolveResponse {
  /** id of the solver that produced the run */
  solverId: string;
  /** ordered sequence of grid points from start to goal (empty when success=false) */
  path: Point[];
  /** number of cells the solver visited */
  visited: number;
  /** number of cells the solver expanded / explored */
  explored: number;
  /** wall-clock duration of the solve in milliseconds */
  elapsedMs: number;
  /** whether the solver actually reached the goal */
  success: boolean;
}

// ============================================
// WebSocket / STOMP Frame DTOs
// ============================================

/**
 * STOMP frame published to /topic/plugins/failures whenever a plugin throws during one
 * of its lifecycle phases. Lets the front-end surface plugin failures as toasts or banner
 * alerts instead of leaving them buried in server logs.
 */
export interface PluginFailedFrame {
  /** id from the plugin's manifest (or a synthetic id for failures that occur before manifest read) */
  pluginId: string;
  /** version from the plugin's manifest, or empty when manifest read failed */
  pluginVersion: string;
  /** which lifecycle phase failed: DISCOVER, INIT, REGISTER_ALGORITHMS, START, or STOP */
  phase: 'DISCOVER' | 'INIT' | 'REGISTER_ALGORITHMS' | 'START' | 'STOP' | string;
  /** fully-qualified class name of the throwable */
  errorClass: string;
  /** the throwable's message (may be null) */
  errorMessage: string | null;
  /** epoch-millis when the failure was published */
  timestamp: number;
}

/**
 * STOMP frame published to /topic/session/{id}/player after a successful player move.
 */
export interface MoveFrame {
  /** id of the session the move belongs to */
  sessionId: string; // UUID
  /** previous player position */
  from: Point;
  /** new player position */
  to: Point;
}

/**
 * STOMP frame published to /topic/maze/{id}/solver when a solver finishes a run.
 */
export interface SolvedFrame {
  /** id of the maze that was solved */
  mazeId: string; // UUID
  /** id of the solver that produced the run */
  solverId: string;
  /** length of the solution path (0 when success=false) */
  pathLength: number;
  /** whether the solver actually reached the goal */
  succ