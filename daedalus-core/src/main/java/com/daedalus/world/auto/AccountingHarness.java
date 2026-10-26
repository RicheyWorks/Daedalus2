// SPDX-License-Identifier: MIT

package com.daedalus.world.auto;

import java.util.Set;

/**
 * Fails the build when discovery lists a capability the drive script never ran.
 */
public final class AccountingHarness {

    private AccountingHarness() {
    }

    public static AccountingReport account(Set<String> discovered, Set<String> driven) {
        return new AccountingReport(discovered, driven);
    }

    public static AccountingReport account(CapabilityRegistry registry, Set<String> driven) {
        return account(registry.discover(), driven);
    }

    public static void requireAccounted(AccountingReport report) {
        if (report.unaccountedCount() > 0) {
            throw new AssertionError("UNACCOUNTED=" + report.unaccountedCount()
                    + " " + report.unaccounted());
        }
    }
}
