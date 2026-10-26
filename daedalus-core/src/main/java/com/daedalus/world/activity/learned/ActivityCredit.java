// SPDX-License-Identifier: MIT

package com.daedalus.world.activity.learned;

/**
 * Credits one finished activity to one creature or plant.
 * Games depend on this, not on a ledger class, so any host can keep the exactly-once guard.
 */
public interface ActivityCredit {

    /**
     * Credits {@code result} once.
     *
     * @throws ActivityCreditException when this attempt was already credited to this subject
     */
    ActivityResultReceipt credit(ActivityResult result);

    /**
     * Reloads a receipt the host already persisted. The same receipt may be remembered again.
     * A different body for the same attempt and subject is refused.
     */
    void remember(ActivityResultReceipt receipt);
}
