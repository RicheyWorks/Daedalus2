#!/usr/bin/env python3
"""
Daedalus Plugin Architecture Specification PDF Generator
Professional, print-ready document with code samples, diagrams, and best practices.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, Color
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Preformatted, KeepTogether, ListFlowable, ListItem, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.colors import grey
import os

# Colors
PRIMARY_BLUE = HexColor("#1a365d")
ACCENT_TEAL = HexColor("#319795")
LIGHT_BG = HexColor("#f7fafc")
CODE_BG = HexColor("#edf2f7")
DARK_TEXT = HexColor("#2d3748")
BORDER = HexColor("#cbd5e0")

def create_styles():
    styles = getSampleStyleSheet()
    
    # Cover title
    styles.add(ParagraphStyle(
        name='CoverTitle',
        parent=styles['Title'],
        fontSize=28,
        textColor=PRIMARY_BLUE,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    # Cover subtitle
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=ACCENT_TEAL,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    ))
    
    # Section heading
    styles.add(ParagraphStyle(
        name='SectionHead',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=PRIMARY_BLUE,
        spaceBefore=18,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        borderPadding=4,
        leftIndent=0
    ))
    
    # Subsection
    styles.add(ParagraphStyle(
        name='SubHead',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=ACCENT_TEAL,
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))
    
    # Body text justified
    styles.add(ParagraphStyle(
        name='BodyJust',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_TEXT,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        leading=14
    ))
    
    # Code block style
    styles.add(ParagraphStyle(
        name='CodeBlock',
        parent=styles['Code'],
        fontSize=8,
        fontName='Courier',
        textColor=DARK_TEXT,
        backColor=CODE_BG,
        leftIndent=8,
        rightIndent=8,
        spaceBefore=6,
        spaceAfter=6,
        leading=11
    ))
    
    # Inline code
    styles.add(ParagraphStyle(
        name='InlineCode',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Courier',
        textColor=HexColor("#c53030"),
        backColor=CODE_BG
    ))
    
    # Note/callout
    styles.add(ParagraphStyle(
        name='Note',
        parent=styles['Normal'],
        fontSize=9,
        textColor=HexColor("#744210"),
        backColor=HexColor("#fefcbf"),
        borderPadding=8,
        leftIndent=10,
        rightIndent=10,
        spaceBefore=8,
        spaceAfter=8
    ))
    
    # Footer
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=grey,
        alignment=TA_CENTER
    ))
    
    # TOC entry
    styles.add(ParagraphStyle(
        name='TOCEntry',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DARK_TEXT,
        spaceAfter=4
    ))
    
    return styles

def add_page_number(canvas, doc):
    """Header and footer on every page."""
    canvas.saveState()
    page_num = canvas.getPageNumber()
    
    # Header line
    canvas.setStrokeColor(ACCENT_TEAL)
    canvas.setLineWidth(1.5)
    canvas.line(0.75*inch, letter[1] - 0.5*inch, letter[0] - 0.75*inch, letter[1] - 0.5*inch)
    
    # Header text
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(PRIMARY_BLUE)
    canvas.drawString(0.75*inch, letter[1] - 0.4*inch, "DAEDALUS PLUGIN ARCHITECTURE SPECIFICATION v1.0")
    canvas.drawRightString(letter[0] - 0.75*inch, letter[1] - 0.4*inch, "Confidential — Internal Use")
    
    # Footer
    canvas.setStrokeColor(BORDER)
    canvas.line(0.75*inch, 0.6*inch, letter[0] - 0.75*inch, 0.6*inch)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(grey)
    canvas.drawCentredString(letter[0]/2, 0.4*inch, f"Page {page_num}")
    
    canvas.restoreState()

def create_code_block(code_text, styles):
    """Create a styled code block with border."""
    # Use Preformatted inside a table for border/background control
    lines = code_text.strip().split('\n')
    formatted = '<br/>'.join(line.replace('<', '&lt;').replace('>', '&gt;') for line in lines)
    
    p = Paragraph(formatted, styles['CodeBlock'])
    
    data = [[p]]
    t = Table(data, colWidths=[6.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t

def build_pdf():
    styles = create_styles()
    story = []
    
    # ========== COVER PAGE ==========
    story.append(Spacer(1, 1.2*inch))
    story.append(Paragraph("DAEDALUS", styles['CoverTitle']))
    story.append(Paragraph("Procedural Maze Engine", styles['CoverSubtitle']))
    story.append(Spacer(1, 0.4*inch))
    story.append(HRFlowable(width="60%", thickness=2, color=ACCENT_TEAL, spaceBefore=10, spaceAfter=10))
    story.append(Paragraph("PLUGIN ARCHITECTURE<br/>SPECIFICATION", styles['CoverTitle']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Version 1.0 — May 2026", styles['CoverSubtitle']))
    story.append(Spacer(1, 0.8*inch))
    
    # Abstract box
    abstract = """<b>Abstract.</b> The Daedalus plugin system delivers a production-grade, Spring-native 
    extension framework for the maze generation and solving platform. Plugins can register new generators 
    and solvers, subscribe to lifecycle and gameplay events, expose REST endpoints and UI themes, and 
    participate in the full Spring application context — all discovered via standard Java ServiceLoader 
    with optional external JAR loading and explicit lifecycle management."""
    story.append(Paragraph(abstract, styles['BodyJust']))
    
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("<i>Document Status: Final — Approved for Implementation</i>", 
                           ParagraphStyle('Center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9)))
    story.append(PageBreak())
    
    # ========== TABLE OF CONTENTS ==========
    story.append(Paragraph("Table of Contents", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=12))
    
    toc_items = [
        "1. Introduction &amp; Design Goals",
        "2. Core Components",
        "   2.1 MazePlugin — The Service Provider Interface",
        "   2.2 PluginManifest — Metadata &amp; Dependency Declaration",
        "   2.3 PluginContext — The Service Handle",
        "   2.4 AbstractPlugin — Convenience Base Class",
        "   2.5 PluginLifecycle — Internal State Machine",
        "3. Plugin Lifecycle &amp; State Transitions",
        "4. Extension Points in Detail",
        "5. Discovery, ClassLoading &amp; Deployment Model",
        "6. Worked Example: FractalBiomePlugin",
        "7. Best Practices, Security &amp; Isolation",
        "8. Formal Guarantees &amp; Audit Surface",
        "9. Appendix: Full Source Listings"
    ]
    for item in toc_items:
        story.append(Paragraph(item, styles['TOCEntry']))
    
    story.append(PageBreak())
    
    # ========== 1. INTRODUCTION ==========
    story.append(Paragraph("1. Introduction &amp; Design Goals", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    intro = """Daedalus is a modular, Spring Boot-based engine for procedural generation of mazes, 
    dungeons, and related content. The plugin architecture was designed from the ground up to satisfy 
    four primary goals:"""
    story.append(Paragraph(intro, styles['BodyJust']))
    
    goals = [
        "<b>Extensibility without Forking</b> — Third parties must be able to add new generators, solvers, visual themes, and even gameplay mechanics without modifying the core engine.",
        "<b>Spring-Native Integration</b> — Plugins are not isolated black boxes; they receive full access to the Spring ApplicationContext, event bus, and can contribute their own @Beans, @RestControllers, and @EventListeners.",
        "<b>Explicit &amp; Observable Lifecycle</b> — Every plugin goes through a well-defined state machine (DISCOVERED → INITIALIZED → REGISTERED → STARTED → STOPPED) with clear hooks and failure semantics.",
        "<b>Production Safety</b> — Strong typing via registries, dependency declaration, resource cleanup contracts, and the ability to run external plugins under a separate classloader."
    ]
    for g in goals:
        story.append(Paragraph("• " + g, styles['BodyJust']))
    
    story.append(Spacer(1, 8))
    note = """<b>Design Note:</b> The architecture deliberately avoids heavy OSGi or custom module systems. 
    Instead it leverages the battle-tested Java ServiceLoader for discovery and Spring’s own extension 
    points for runtime wiring. This keeps the cognitive load low while still delivering enterprise-grade 
    capabilities."""
    story.append(Paragraph(note, styles['Note']))
    
    # ========== 2. CORE COMPONENTS ==========
    story.append(Paragraph("2. Core Components", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    # 2.1 MazePlugin
    story.append(Paragraph("2.1 MazePlugin — The Service Provider Interface", styles['SubHead']))
    
    desc = """<code>MazePlugin</code> is the sole extension point. All plugins must implement this interface 
    (directly or via <code>AbstractPlugin</code>). It uses default methods so implementors only override 
    what they need."""
    story.append(Paragraph(desc, styles['BodyJust']))
    
    code1 = """package com.daedalus.plugin;

import com.daedalus.model.AlgorithmDescriptor;
import java.util.List;

public interface MazePlugin {

    PluginManifest manifest();

    default void init(PluginContext ctx) {}

    default void registerAlgorithms(PluginContext ctx) {}

    default void start(PluginContext ctx) {}

    default void stop(PluginContext ctx) {}

    default List<AlgorithmDescriptor> contributedAlgorithms() { return List.of(); }
}"""
    story.append(create_code_block(code1, styles))
    
    story.append(Paragraph("<b>Lifecycle contract:</b> <code>init</code> → <code>registerAlgorithms</code> → <code>start</code> → … → <code>stop</code>. The framework guarantees this ordering and that <code>stop</code> is called even on failure paths (via try/finally).", styles['BodyJust']))
    
    # 2.2 PluginManifest
    story.append(Paragraph("2.2 PluginManifest — Metadata &amp; Dependency Declaration", styles['SubHead']))
    
    code2 = """public record PluginManifest(
        String id,           // unique slug, e.g. "biome-generators"
        String displayName,
        String version,
        String author,
        String description,
        String[] requires    // ids of other plugins loaded first
) {
    public PluginManifest(...) { this(..., new String[0]); }
}"""
    story.append(create_code_block(code2, styles))
    
    story.append(Paragraph("Manifests are exposed via <code>GET /api/plugins</code> and used by the PluginManager to enforce load order and detect missing dependencies before any plugin code executes.", styles['BodyJust']))
    
    # 2.3 PluginContext
    story.append(Paragraph("2.3 PluginContext — The Service Handle", styles['SubHead']))
    
    ctx_desc = """A lightweight, final handle passed to every lifecycle method. It deliberately exposes only 
    four capabilities, keeping the plugin API narrow and auditable:"""
    story.append(Paragraph(ctx_desc, styles['BodyJust']))
    
    code3 = """public final class PluginContext {
    private final ApplicationContext spring;
    private final GeneratorRegistry generators;
    private final SolverRegistry solvers;

    public GeneratorRegistry generators() { return generators; }
    public SolverRegistry solvers()       { return solvers; }
    public ApplicationContext beans()     { return spring; }
    public ApplicationEventPublisher events() { return spring; }

    public <T> T bean(Class<T> type) { return spring.getBean(type); }
}"""
    story.append(create_code_block(code3, styles))
    
    story.append(Paragraph("<b>Why not inject everything?</b> Explicit methods make it obvious what a plugin is allowed to do and simplify testing/mocking of the context itself.", styles['BodyJust']))
    
    # 2.4 & 2.5
    story.append(Paragraph("2.4 AbstractPlugin &amp; 2.5 PluginLifecycle", styles['SubHead']))
    
    code4 = """public abstract class AbstractPlugin implements MazePlugin {
    protected PluginContext context;

    @Override
    public void init(PluginContext ctx) {
        this.context = ctx;
    }
}

public enum PluginLifecycle {
    DISCOVERED, INITIALIZED, REGISTERED, STARTED, STOPPED, FAILED
}"""
    story.append(create_code_block(code4, styles))
    
    story.append(Paragraph("The enum is used internally by the PluginManager to track progress and to decide whether a failed plugin should block startup or be isolated.", styles['BodyJust']))
    
    story.append(PageBreak())
    
    # ========== 3. LIFECYCLE ==========
    story.append(Paragraph("3. Plugin Lifecycle &amp; State Transitions", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    story.append(Paragraph("The framework maintains a strict state machine for every discovered plugin:", styles['BodyJust']))
    
    # Lifecycle table
    lifecycle_data = [
        ['State', 'Trigger', 'Hook Called', 'Guarantees'],
        ['DISCOVERED', 'ServiceLoader + manifest parse', '—', 'Manifest validated, dependencies checked'],
        ['INITIALIZED', 'All dependencies STARTED', 'init(ctx)', 'context != null, safe to store'],
        ['REGISTERED', 'After init batch', 'registerAlgorithms(ctx)', 'Generators/solvers visible to engine'],
        ['STARTED', 'Spring context refreshed', 'start(ctx)', 'Full event bus & REST active'],
        ['STOPPED', 'Shutdown hook or explicit', 'stop(ctx)', 'Resources released, listeners unsubscribed'],
        ['FAILED', 'Any exception in prior phase', '—', 'Isolated; other plugins continue']
    ]
    
    t = Table(lifecycle_data, colWidths=[1.1*inch, 1.8*inch, 1.6*inch, 2.0*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_BG),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("<b>Failure Semantics:</b> A plugin that throws in <code>registerAlgorithms</code> is marked FAILED and its contributions are rolled back. The rest of the system continues. This allows graceful degradation (e.g., a optional visual theme plugin can fail without breaking core maze generation).", styles['BodyJust']))
    
    # ========== 4. EXTENSION POINTS ==========
    story.append(Paragraph("4. Extension Points in Detail", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    story.append(Paragraph("<b>4.1 Algorithm Registration</b>", styles['SubHead']))
    story.append(Paragraph("The primary purpose of most plugins is to contribute new <code>Generator</code> or <code>Solver</code> implementations. The <code>PluginContext</code> provides typed registries:", styles['BodyJust']))
    
    code5 = """// Inside registerAlgorithms(PluginContext ctx)
ctx.generators().register(new FractalCaveGenerator());
ctx.solvers().register(new AStarWithBiomeHeuristic());"""
    story.append(create_code_block(code5, styles))
    
    story.append(Paragraph("<b>4.2 Event Subscription</b>", styles['SubHead']))
    story.append(Paragraph("Because <code>events()</code> returns the Spring <code>ApplicationEventPublisher</code>, plugins can both publish custom events and subscribe via <code>@EventListener</code> methods on their own Spring beans (or even on the plugin class itself if it is a <code>@Component</code>).", styles['BodyJust']))
    
    story.append(Paragraph("<b>4.3 Full Spring Participation</b>", styles['SubHead']))
    story.append(Paragraph("Plugin JARs are added to the classloader <i>before</i> the Spring context is refreshed. Therefore a plugin can contain any number of <code>@Configuration</code>, <code>@RestController</code>, <code>@Service</code>, or <code>@EventListener</code> classes that will be picked up automatically. The only requirement is that the plugin’s package is scanned (usually by listing it in the core <code>@SpringBootApplication</code> scanBasePackages or by using a marker annotation).", styles['BodyJust']))
    
    story.append(Paragraph("<b>4.4 UI / AlgorithmDescriptor Contribution</b>", styles['SubHead']))
    story.append(Paragraph("The optional <code>contributedAlgorithms()</code> method returns metadata used by the web UI to list available algorithms without instantiating them. This keeps the plugin lightweight until the user actually selects it.", styles['BodyJust']))
    
    # ========== 5. DISCOVERY ==========
    story.append(Paragraph("5. Discovery, ClassLoading &amp; Deployment Model", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    story.append(Paragraph("<b>Built-in Plugins</b>", styles['SubHead']))
    story.append(Paragraph("Core plugins are declared in <code>META-INF/services/com.daedalus.plugin.MazePlugin</code> inside the main application JAR. They are loaded with the application classloader.", styles['BodyJust']))
    
    story.append(Paragraph("<b>External Plugins</b>", styles['SubHead']))
    story.append(Paragraph("Drop a JAR into the <code>plugins/</code> directory next to the application JAR. At startup the PluginManager:", styles['BodyJust']))
    
    ext_steps = [
        "Scans <code>plugins/*.jar</code> for a valid manifest and ServiceLoader entry.",
        "Creates a new <code>URLClassLoader</code> for the plugin (parent = application loader) — strong isolation of plugin-private classes.",
        "Registers the plugin’s SPI implementation.",
        "Proceeds with normal lifecycle."
    ]
    for s in ext_steps:
        story.append(Paragraph("• " + s, styles['BodyJust']))
    
    story.append(Paragraph("<b>Hot-Reload Note:</b> Current design does not support runtime reloading of plugin JARs. A restart is required. Future versions may add a watched directory + dynamic classloader swap with quiescence guarantees.", styles['Note']))
    
    story.append(PageBreak())
    
    # ========== 6. WORKED EXAMPLE ==========
    story.append(Paragraph("6. Worked Example: FractalBiomePlugin", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    story.append(Paragraph("Below is a minimal but complete plugin that adds three new biome-aware generators and listens for generation events to log statistics.", styles['BodyJust']))
    
    code6 = """package com.example.fractalbiome;

import com.daedalus.plugin.*;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@PluginManifest(
    id = "fractal-biome",
    displayName = "Fractal Biome Generators",
    version = "1.2.0",
    author = "Daedalus Labs",
    description = "Adds cave, forest and crystal biome generators"
)
public class FractalBiomePlugin extends AbstractPlugin {

    @Override
    public void registerAlgorithms(PluginContext ctx) {
        ctx.generators().register(new FractalCaveGenerator());
        ctx.generators().register(new ForestCanopyGenerator());
        ctx.generators().register(new CrystalCavernGenerator());
    }

    @Component
    public static class GenerationStatsListener {
        @EventListener
        public void onMazeGenerated(MazeGeneratedEvent e) {
            // custom telemetry, metrics, etc.
            System.out.printf("Generated %s in %dms%n", e.getAlgorithm(), e.getDuration());
        }
    }
}"""
    story.append(create_code_block(code6, styles))
    
    story.append(Paragraph("The <code>@PluginManifest</code> annotation (or a <code>plugin.properties</code> file) is read by the discovery layer to populate the <code>PluginManifest</code> record without forcing the plugin class to be instantiated early.", styles['BodyJust']))
    
    # ========== 7. BEST PRACTICES ==========
    story.append(Paragraph("7. Best Practices, Security &amp; Isolation", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    practices = [
        "<b>Resource Management</b> — Always release threads, file handles, and Spring subscriptions in <code>stop()</code>. The framework does not guarantee GC will run promptly after plugin unload.",
        "<b>Minimal Surface</b> — Prefer registering algorithms over exposing full controllers. Every additional Spring bean increases the attack surface.",
        "<b>Versioning</b> — Follow semantic versioning in the manifest. The <code>requires</code> array should pin major versions only.",
        "<b>Exception Hygiene</b> — Never let checked exceptions escape lifecycle methods. Wrap and log; let the framework mark the plugin FAILED.",
        "<b>Classloader Hygiene</b> — Do not store static references to classes loaded from the plugin classloader; they become unreachable after stop and can cause memory leaks.",
        "<b>Testing</b> — Unit test your plugin logic in isolation. Integration tests should use a test <code>PluginContext</code> that supplies mock registries and an in-memory Spring context."
    ]
    for p in practices:
        story.append(Paragraph("• " + p, styles['BodyJust']))
    
    # ========== 8. FORMAL GUARANTEES ==========
    story.append(Paragraph("8. Formal Guarantees &amp; Audit Surface", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    story.append(Paragraph("The plugin system provides the following formal properties that can be audited or proven:", styles['BodyJust']))
    
    guarantees = [
        "<b>Ordering Invariant</b> — For any two plugins A and B, if A appears in B.requires, then A reaches STARTED before B.init is called (proven by topological sort in PluginManager).",
        "<b>Isolation</b> — Classes defined inside an external plugin JAR are never visible to other plugins or the core unless explicitly exported via the plugin’s package list.",
        "<b>Rollback</b> — Any exception thrown from registerAlgorithms triggers automatic un-registration of any partial contributions made by that plugin before the exception.",
        "<b>Event Delivery</b> — All @EventListener methods contributed by a plugin receive events only after the plugin has reached STARTED state."
    ]
    for g in guarantees:
        story.append(Paragraph("• " + g, styles['BodyJust']))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>Audit Surface:</b> The only runtime reflection used is ServiceLoader and Spring’s standard component scanning. No custom bytecode manipulation or unsafe operations are performed on plugin code.", styles['BodyJust']))
    
    story.append(PageBreak())
    
    # ========== 9. APPENDIX ==========
    story.append(Paragraph("9. Appendix: Full Source Listings", styles['SectionHead']))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_TEAL, spaceAfter=10))
    
    story.append(Paragraph("The following listings are the exact source files distributed with Daedalus 1.0.", styles['BodyJust']))
    
    # PluginContext full
    story.append(Paragraph("PluginContext.java", styles['SubHead']))
    full_ctx = """package com.daedalus.plugin;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.solver.solvers.SolverRegistry;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationEventPublisher;

public final class PluginContext {
    private final ApplicationContext spring;
    private final GeneratorRegistry generators;
    private final SolverRegistry solvers;

    public PluginContext(ApplicationContext spring,
                         GeneratorRegistry generators,
                         SolverRegistry solvers) {
        this.spring = spring;
        this.generators = generators;
        this.solvers = solvers;
    }

    public GeneratorRegistry generators() { return generators; }
    public SolverRegistry solvers()       { return solvers; }
    public ApplicationContext beans()     { return spring; }
    public ApplicationEventPublisher events() { return spring; }

    public <T> T bean(Class<T> type) {
        return spring.getBean(type);
    }
}"""
    story.append(create_code_block(full_ctx, styles))
    
    story.append(Spacer(1, 12))
    story.append(Paragraph("MazePlugin.java (abridged)", styles['SubHead']))
    full_maze = """package com.daedalus.plugin;

import com.daedalus.model.AlgorithmDescriptor;
import java.util.List;

public interface MazePlugin {
    PluginManifest manifest();
    default void init(PluginContext ctx) {}
    default void registerAlgorithms(PluginContext ctx) {}
    default void start(PluginContext ctx) {}
    default void stop(PluginContext ctx) {}
    default List<AlgorithmDescriptor> contributedAlgorithms() { return List.of(); }
}"""
    story.append(create_code_block(full_maze, styles))
    
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_BLUE, spaceAfter=10))
    story.append(Paragraph("<b>End of Specification</b>", ParagraphStyle('End', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, textColor=PRIMARY_BLUE)))
    story.append(Paragraph("Questions? Contact plugins@daedalus.engine", ParagraphStyle('End2', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=grey)))
    
    # Build
    output_path = "/home/workdir/artifacts/daedalus-plugin-architecture.pdf"
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.7*inch,
        leftMargin=0.7*inch,
        topMargin=0.7*inch,
        bottomMargin=0.7*inch,
        title="Daedalus Plugin Architecture Specification v1.0",
        author="Daedalus Engineering Team"
    )
    
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"PDF generated successfully: {output_path}")
    return output_path

if __name__ == "__main__":
    build_pdf()