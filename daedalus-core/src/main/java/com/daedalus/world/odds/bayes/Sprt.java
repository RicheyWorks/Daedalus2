// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.bayes;

/**
 * Wald's sequential probability ratio test between a fair coin ({@code p0}) and a rigged one ({@code p1}). Each flip
 * adds ln(p1/p0) for heads or ln((1-p1)/(1-p0)) for tails to the log-likelihood ratio; the test stops at
 * A = ln((1-beta)/alpha) (call it rigged) or B = ln(beta/(1-alpha)) (call it fair). Mutable, one per coin.
 */
public final class Sprt {

    /** What the test says so far. */
    public enum Decision { CONTINUE, FAIR, RIGGED }

    private final double headsStep;
    private final double tailsStep;
    private final double upper;
    private final double lower;
    private double llr;
    private int flips;
    private int heads;

    public Sprt(double p0, double p1, double alpha, double beta) {
        if (!(p0 > 0 && p0 < 1 && p1 > 0 && p1 < 1) || p0 == p1) {
            throw new IllegalArgumentException("need 0 < p0, p1 < 1 and p0 != p1");
        }
        if (!(alpha > 0 && alpha < 0.5 && beta > 0 && beta < 0.5)) {
            throw new IllegalArgumentException("alpha and beta must be in (0, 0.5)");
        }
        this.headsStep = Math.log(p1 / p0);
        this.tailsStep = Math.log((1 - p1) / (1 - p0));
        this.upper = Math.log((1 - beta) / alpha);
        this.lower = Math.log(beta / (1 - alpha));
    }

    /** Records one flip and returns the decision after it. */
    public Decision record(boolean isHeads) {
        llr += isHeads ? headsStep : tailsStep;
        flips++;
        if (isHeads) {
            heads++;
        }
        return decision();
    }

    public Decision decision() {
        if (llr >= upper) {
            return Decision.RIGGED;
        }
        if (llr <= lower) {
            return Decision.FAIR;
        }
        return Decision.CONTINUE;
    }

    public double llr() {
        return llr;
    }

    public int flips() {
        return flips;
    }

    public int heads() {
        return heads;
    }

    public double upper() {
        return upper;
    }

    public double lower() {
        return lower;
    }
}
