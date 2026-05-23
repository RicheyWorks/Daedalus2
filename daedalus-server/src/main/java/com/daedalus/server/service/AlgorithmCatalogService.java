// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.solver.solvers.SolverRegistry;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/** Read-only catalog of every registered algorithm — surfaced to UI and REST consumers. */
@Service
public class AlgorithmCatalogService {

    private final GeneratorRegistry generators;
    private final SolverRegistry solvers;

    public AlgorithmCatalogService(GeneratorRegistry generators, SolverRegistry solvers) {
        this.generators = generators;
        this.solvers = solvers;
    }

    public List<AlgorithmDescriptor> generators() { return generators.descriptors(); }
    public List<AlgorithmDescriptor> solvers()    { return solvers.descriptors(); }

    public List<AlgorithmDescriptor> all() {
        List<AlgorithmDescriptor> out = new ArrayList<>();
        out.addAll(generators.descriptors());
        out.addAll(solvers.descriptors());
        return out;
    }
}
