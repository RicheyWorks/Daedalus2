// SPDX-License-Identifier: MIT

package com.daedalus.examples.biome;

import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.plugin.AbstractPlugin;
import com.daedalus.plugin.PluginContext;
import com.daedalus.plugin.PluginManifest;
import com.daedalus.plugin.events.MazeGeneratedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEvent;
import org.springframework.context.ApplicationListener;
import org.springframework.context.PayloadApplicationEvent;
import org.springframework.context.event.ApplicationEventMulticaster;

import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Reference plugin — registers two biome-themed generators and subscribes
 * to {@link MazeGeneratedEvent} to log a one-line summary per generation.
 *
 * <p>This class is the canonical worked example for the README's "Writing a
 * plugin" section. It walks through every interesting touchpoint of the SPI:
 *
 * <ul>
 *   <li><b>{@link #manifest()}</b> — identity card surfaced through
 *       {@code GET /api/v1/plugins}.</li>
 *   <li><b>{@link #registerAlgorithms(PluginContext)}</b> — adds the two biome
 *       generators to the host's {@code GeneratorRegistry}; they appear in
 *       {@code GET /api/v1/algorithms} and the desktop UI dropdown
 *       automatically.</li>
 *   <li><b>{@link #start(PluginContext)}</b> — subscribes to events. See the
 *       implementation note below.</li>
 *   <li><b>{@link #stop(PluginContext)}</b> — disarms the listener so it goes
 *       quiet on shutdown / hot reload. Spring's
 *       {@link ApplicationEventMulticaster#removeApplicationListener} would
 *       work too, but it requires the plugin to retain the listener reference
 *       on its own state — the disarm flag is functionally equivalent and
 *       keeps the lifecycle methods one line each.</li>
 *   <li><b>{@link #contributedAlgorithms()}</b> — descriptor list for diagnostics
 *       endpoints that want to enumerate per-plugin contributions without
 *       walking the shared registry.</li>
 * </ul>
 *
 * <p><b>Why not {@code @EventListener}?</b> Plugin instances are loaded via
 * {@link java.util.ServiceLoader}, not by Spring's bean factory. Spring's
 * {@code EventListenerMethodProcessor} only scans actual beans, so an
 * annotation on this class would be silently ignored. Registering an
 * {@link ApplicationListener} programmatically through Spring's
 * {@link ApplicationEventMulticaster} (a well-known bean Spring always
 * registers under the name {@code applicationEventMulticaster}) is the
 * supported path for plugin-side event consumption.
 *
 * @since 1.0
 */
public final class BiomeGeneratorPlugin extends AbstractPlugin {

    private static final Logger log = LoggerFactory.getLogger(BiomeGeneratorPlugin.class);

    private static final String ID = "biome-generators";
    private static final String DISPLAY = "Biome Generators";
    private static final String VERSION = "1.0.0";
    private static final String AUTHOR = "Daedalus examples";
    private static final String DESCRIPTION =
            "Reference plugin: forest-biome + desert-biome generators with " +
            "a MazeGeneratedEvent listener that logs one line per generation.";

    private final ForestBiomeGenerator forest = new ForestBiomeGenerator();
    private final DesertBiomeGenerator desert = new DesertBiomeGenerator();

    /** Toggled off in {@link #stop} so the listener becomes a no-op after shutdown. */
    private final AtomicBoolean armed = new AtomicBoolean(false);

    @Override
    public PluginManifest manifest() {
        return new PluginManifest(ID, DISPLAY, VERSION, AUTHOR, DESCRIPTION);
    }

    @Override
    public void registerAlgorithms(PluginContext ctx) {
        ctx.generators().register(forest);
        ctx.generators().register(desert);
        log.info("Biome plugin: registered generators [{}, {}]",
                forest.id(), desert.id());
    }

    @Override
    public void start(PluginContext ctx) {
        armed.set(true);

        // Programmatic listener registration (see class Javadoc for why).
        // ApplicationEventMulticaster is the public Spring bean responsible
        // for fan-out; addApplicationListener forwards every fired event
        // through this listener for the lifetime of the context.
        // We don't filter by which generator fired the event — every
        // MazeGeneratedEvent flows through, so operators can see proof the
        // plugin is alive even when the host is generating a non-biome maze.
        ApplicationEventMulticaster multicaster =
                ctx.bean(ApplicationEventMulticaster.class);
        multicaster.addApplicationListener(new MazeGeneratedListener(armed));

        log.info("Biome plugin: subscribed to MazeGeneratedEvent");
    }

    @Override
    public void stop(PluginContext ctx) {
        armed.set(false);
        log.info("Biome plugin: stopped (listener disarmed)");
    }

    @Override
    public List<AlgorithmDescriptor> contributedAlgorithms() {
        return List.of(forest.descriptor(), desert.descriptor());
    }

    /**
     * One-line summary listener. Kept as a private static class (rather than
     * a lambda) so its identity is stable in heap dumps and Spring's listener
     * list — easier to spot when debugging hot reloads.
     *
     * <p>{@code MazeGeneratedEvent} is a Daedalus-domain POJO that does
     * <em>not</em> extend {@link ApplicationEvent}; Spring wraps it in a
     * {@link PayloadApplicationEvent} when the host calls
     * {@code applicationContext.publishEvent(...)}. The {@code @EventListener}
     * annotation processor would unwrap that automatically, but a
     * programmatic listener has to do it itself — hence the payload check
     * below.
     */
    private static final class MazeGeneratedListener
            implements ApplicationListener<ApplicationEvent> {

        private final AtomicBoolean armed;

        MazeGeneratedListener(AtomicBoolean armed) {
            this.armed = armed;
        }

        @Override
        public void onApplicationEvent(ApplicationEvent event) {
            if (!armed.get()) return;

            // Unwrap PayloadApplicationEvent if the host published a POJO event.
            // Fall back to the event itself so this listener also works if
            // PluginEvent is ever promoted to extend ApplicationEvent directly.
            Object payload = (event instanceof PayloadApplicationEvent<?> pae)
                    ? pae.getPayload()
                    : event;
            if (!(payload instanceof MazeGeneratedEvent e)) return;

            var md = e.metadata();
            var st = e.stats();
            log.info("[biome] maze generated id={} gen={} dims={}x{} seed={} visited={} backtracks={}",
                    md.id(), md.generatorId(),
                    md.rows(), md.cols(),
                    md.seed(),
                    st.cellsVisited(),
                    st.backtrackCount());
        }
    }
}
