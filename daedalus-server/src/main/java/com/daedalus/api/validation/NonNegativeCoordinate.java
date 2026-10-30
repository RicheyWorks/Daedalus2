// SPDX-License-Identifier: MIT

package com.daedalus.api.validation;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Field-level Bean Validation constraint that asserts a {@link com.daedalus.model.Point}
 * has both row and col {@code >= 0}.
 *
 * <p>Lives in {@code daedalus-server}'s validation package — by design, not next to
 * {@code Point} in {@code daedalus-core}. The core module is intentionally framework-free
 * (no {@code jakarta.validation} dependency), so per-field annotations on {@code Point}
 * itself are off the table. This composite + its
 * {@link NonNegativeCoordinateValidator} reach in via the public {@code row()} /
 * {@code col()} accessors instead, preserving the dependency boundary.
 *
 * <p>Null targets pass the check — pair with {@code @NotNull} on the same field if the
 * coordinate is required (as {@code MoveRequest} does).
 *
 * <p>Catches negative coordinates at the API surface so they surface as a structured
 * 400 with a {@code fieldErrors} entry, rather than silently flipping a downstream
 * {@code tryMove(...)} call to {@code false}.
 *
 * @since 1.0
 */
@Documented
@Target({ ElementType.FIELD, ElementType.PARAMETER, ElementType.RECORD_COMPONENT })
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = NonNegativeCoordinateValidator.class)
public @interface NonNegativeCoordinate {

    String message() default "row and col must both be non-negative";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}
