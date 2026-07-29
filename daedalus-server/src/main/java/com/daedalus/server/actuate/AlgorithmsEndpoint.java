// SPDX-License-Identifier: MIT

package com.daedalus.server.actuate;

import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.server.service.AlgorithmCatalogService;
import org.springframework.boot.actuate.endpoint.annotation.Endpoint;
import org.springframework.boot.actuate.endpoint.annotation.ReadOperation;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

/**
 * {@code /actuator/algorithms} — registry observability (audit recommendation §2.1.2, filed
 * for LoadBalancer Lab: "what algorithms does this instance actually have right now?").
 *
 * <p>This deliberately answers a different question from {@code GET /api/v1/algorithms}. The
 * REST endpoint is the <em>product</em> surface — versioned, rate-limit-adjacent, part of the
 * OpenAPI contract. This is the <em>operational</em> surface: it lives with health and
 * prometheus, follows actuator's exposure rules per profile (visible in dev where exposure is
 * {@code *}; absent in prod unless added to the include list alongside health/info/prometheus),
 * and is reachable over JMX when {@code spring.jmx.enabled} is on — actuator endpoints get
 * both transports from one definition, which is why this is an {@code @Endpoint} rather than
 * a hand-rolled MBean.
 *
 * <p>Registries are live: plugins register algorithms at boot, so the counts and ids here
 * reflect what plugin loading actually produced on <em>this</em> instance — the observability
 * gap the audit item was really about.
 */
@Component
@Endpoint(id = "algorithms")
public class AlgorithmsEndpoint {

    private final AlgorithmCatalogService catalog;

    public AlgorithmsEndpoint(AlgorithmCatalogService catalog) {
        this.catalog = catalog;
    }

    @ReadOperation
    public Map<String, Object> algorithms() {
        List<AlgorithmDescriptor> generators = catalog.generators();
        List<AlgorithmDescriptor> solvers = catalog.solvers();
        return Map.of(
                "generatorCount", generators.size(),
                "solverCount", solvers.size(),
                "generators", generators,
                "solvers", solvers);
    }
}
