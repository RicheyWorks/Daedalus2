// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

/**
 * Activity-result v1 namespaces. AUTHORITATIVE results were verified by a named authority and may settle an
 * award; DEVICE_LOCAL results (browser timers, cabinet scores, exported saves) are recorded as contributions
 * only and never pay progression.
 */
public enum ActivityMode { AUTHORITATIVE, DEVICE_LOCAL }
