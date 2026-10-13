package com.daedalus.world.audio;

/** Body class sets the voice range; the genome picks inside it. Bigger bodies, lower voices. */
public enum Species {
    /** Small birds and insects. */
    SONGBIRD(1800, 5200),
    /** Goats, sheep. */
    GOAT(260, 700),
    /** Cattle, yaks. */
    BOVINE(70, 220),
    /** Pigs, boars. */
    SWINE(140, 480),
    /** Poultry. */
    FOWL(500, 1600),
    /** Frogs and toads. */
    AMPHIBIAN(150, 900),
    /** Wolves, dogs. */
    CANID(300, 1200);

    private final double lowHz;
    private final double highHz;

    Species(double lowHz, double highHz) {
        this.lowHz = lowHz;
        this.highHz = highHz;
    }

    /** Lowest fundamental. */
    public double lowHz() {
        return lowHz;
    }

    /** Highest fundamental. */
    public double highHz() {
        return highHz;
    }
}
