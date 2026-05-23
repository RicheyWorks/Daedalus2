// SPDX-License-Identifier: MIT

package com.daedalus.api.validation;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;
import jakarta.validation.ReportAsSingleViolation;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Composite Bean Validation constraint that marks a {@link String} as a Daedalus algorithm
 * identifier — the lower-case-kebab-case form used by the {@code GeneratorRegistry} and
 * {@code SolverRegistry} (e.g. {@code "binary-tree"}, {@code "recursive-backtracker"},
 * {@code "oldest-pick"}).
 *
 * <p>Validates the same contract as {@code @NotBlank + @Pattern(...)} but bundles them
 * into a single annotation so the regex lives in exactly one place. {@link
 * ReportAsSingleViolation} collapses an empty-string failure (which trips both inner
 * constraints) into a single error keyed by the offending field — keeps the
 * {@code fieldErrors} map terse.
 *
 * <p>Apply on {@code @RequestBody} record components, {@code @PathVariable} parameters,
 * and {@code @RequestParam} parameters. Path / query placement requires
 * {@code @Validated} on the surrounding controller class (already enabled on
 * {@code MazeController}).
 *
 * @since 1.0
 */
@Documented
@Target({ ElementType.FIELD, ElementType.PARAMETER, ElementType.RECORD_COMPONENT })
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = {})
@NotBlank
@Pattern(regexp = "^[a-z0-9][a-z0-9-]{0,63}$")
@ReportAsSingleViolation
public @interface AlgorithmId {

    /**
     * Default message — picked so existing tests asserting on substring {@code "lowercase"}
     * remain green after the migration from {@code @NotBlank + @Pattern} to this composite.
     */
    String message() default "must be 1-64 chars, lowercase letters / digits / hyphens, leading hyphen disallowed";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}
