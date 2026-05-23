// SPDX-License-Identifier: MIT

package com.daedalus.api.validation;

import com.daedalus.model.Point;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;

/**
 * Validator backing {@link NonNegativeCoordinate}. Returns {@code true} for null (so the
 * paired {@code @NotNull} controls presence) and for any {@link Point} whose row and col
 * are both {@code >= 0}.
 */
public class NonNegativeCoordinateValidator
        implements ConstraintValidator<NonNegativeCoordinate, Point> {

    @Override
    public boolean isValid(Point value, ConstraintValidatorContext context) {
        if (value == null) {
            return true;   // delegated to @NotNull
        }
        return value.row() >= 0 && value.col() >= 0;
    }
}
