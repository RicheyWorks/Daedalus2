// SPDX-License-Identifier: MIT

package com.daedalus.testsupport;

import java.io.File;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Modifier;
import java.net.URL;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.Comparator;
import java.util.Enumeration;
import java.util.Set;
import java.util.TreeSet;

/**
 * Test-only classpath scanner for roster completeness guards.
 *
 * <h3>Why this exists</h3>
 *
 * <p>The suite-wide property tests ({@code SolverBraidedMazePropertyTest},
 * {@code GeneratorConnectivityTest}) enumerate their subjects in explicit rosters, because core
 * deliberately has no classpath scanner and no {@code ServiceLoader} registration. The hazard is
 * a subject added later and silently left out — which is precisely how Trémaux went untested
 * behind a green suite. A {@code hasSize(N)} tripwire only fires if someone remembers to bump
 * {@code N}; this scan makes the guard structural: any concrete implementation present in the
 * package but missing from the roster fails the build, and exclusions become visible code
 * instead of invisible absence.
 *
 * <p>~30 lines over {@link ClassLoader#getResources}; no new dependency. It only handles
 * directory classpath entries (which is what surefire gives tests) — jar entries would need
 * more, and tests never see production classes from a jar in this reactor.
 */
public final class PackageScan {

    private PackageScan() {
    }

    /**
     * Every concrete (non-abstract, non-interface) top-level class in {@code packageName} that
     * is assignable to {@code supertype}, sorted by name for stable failure messages.
     */
    public static Set<Class<?>> concreteImplementationsIn(String packageName, Class<?> supertype) {
        Set<Class<?>> result = new TreeSet<>(Comparator.comparing(Class::getName));
        String path = packageName.replace('.', '/');
        try {
            Enumeration<URL> roots =
                    Thread.currentThread().getContextClassLoader().getResources(path);
            while (roots.hasMoreElements()) {
                URL root = roots.nextElement();
                if (!"file".equals(root.getProtocol())) {
                    continue; // directory entries only; see class javadoc
                }
                File dir = new File(URLDecoder.decode(root.getFile(), StandardCharsets.UTF_8));
                File[] classFiles = dir.listFiles(
                        (d, name) -> name.endsWith(".class") && !name.contains("$"));
                if (classFiles == null) {
                    continue;
                }
                for (File classFile : classFiles) {
                    String simpleName = classFile.getName()
                            .substring(0, classFile.getName().length() - ".class".length());
                    Class<?> candidate = Class.forName(packageName + "." + simpleName);
                    if (supertype.isAssignableFrom(candidate)
                            && !candidate.isInterface()
                            && !Modifier.isAbstract(candidate.getModifiers())) {
                        result.add(candidate);
                    }
                }
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } catch (ClassNotFoundException e) {
            throw new IllegalStateException("class file present but unloadable", e);
        }
        if (result.isEmpty()) {
            throw new IllegalStateException(
                    "PackageScan found nothing in " + packageName + " — scan is broken, "
                            + "which would make every roster guard vacuously green");
        }
        return result;
    }
}
