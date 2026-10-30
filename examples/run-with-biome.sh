#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# examples/run-with-biome.sh
#
# Builds the reference biome-plugin, drops the resulting JAR into a temp
# plugin directory, and boots the Daedalus server pointing
# daedalus.plugins.directory at that directory.
#
# Usage:
#   ./examples/run-with-biome.sh [server-args...]
#
# Anything you pass on the command line is forwarded to `spring-boot:run`
# via -Dspring-boot.run.arguments=... — useful for ad-hoc profile flips:
#
#   ./examples/run-with-biome.sh --server.port=8090
#
# Requires: Java 21, Maven 3.9+.

set -euo pipefail

# Resolve the repo root from the script location so the helper works from any
# cwd (the README invokes it as ./examples/run-with-biome.sh from the root).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_POM="$REPO_ROOT/examples/biome-plugin/pom.xml"

if [[ ! -f "$PLUGIN_POM" ]]; then
  echo "error: $PLUGIN_POM not found — are you running this from inside a Daedalus checkout?" >&2
  exit 1
fi

# 1. Install the engine + plugin-api into ~/.m2 so the plugin can resolve them
#    at compile time (they're `provided` scope in the plugin pom). Skip tests
#    to keep this fast — the main reactor's tests are run separately by CI.
echo "==> Installing daedalus-plugin-api + daedalus-core into the local Maven repo"
mvn -B -f "$REPO_ROOT/pom.xml" \
    -pl daedalus-plugin-api -am \
    -DskipTests install

# 2. Build the plugin JAR.
echo "==> Building the biome-plugin JAR"
mvn -B -f "$PLUGIN_POM" clean package

PLUGIN_JAR="$(ls -1 "$REPO_ROOT/examples/biome-plugin/target/"*.jar | head -n 1)"
if [[ ! -f "$PLUGIN_JAR" ]]; then
  echo "error: build succeeded but no JAR was produced under examples/biome-plugin/target/" >&2
  exit 1
fi

# 3. Stage the JAR in a fresh plugin directory. mktemp -d is portable across
#    macOS / Linux; we cleanup on exit so repeated runs don't litter /tmp.
PLUGIN_DIR="$(mktemp -d -t daedalus-biome-plugins.XXXXXX)"
trap 'rm -rf "$PLUGIN_DIR"' EXIT
cp "$PLUGIN_JAR" "$PLUGIN_DIR/"
echo "==> Staged $(basename "$PLUGIN_JAR") in $PLUGIN_DIR"

# 4. Forward any user args as spring-boot run arguments. The spring-boot
#    maven plugin parses -Dspring-boot.run.arguments as a COMMA-separated
#    list; space-separated args would be collapsed into a single literal
#    by Spring Boot's argument parser. Hence printf '%s,' + strip-trailing.
RUN_ARGS=""
if [[ $# -gt 0 ]]; then
  RUN_ARGS="-Dspring-boot.run.arguments=$(printf '%s,' "$@" | sed 's/,$//')"
fi

# 5. Boot the server with the plugin dir override. The server's
#    application.yml exposes daedalus.plugins.directory as a configurable
#    property — we pin it via -Dspring-boot.run.jvmArguments so the override
#    is visible to the bound @ConfigurationProperties.
echo "==> Booting daedalus-server with daedalus.plugins.directory=$PLUGIN_DIR"
mvn -B -f "$REPO_ROOT/pom.xml" \
    -pl daedalus-server -am \
    spring-boot:run \
    "-Dspring-boot.run.jvmArguments=-Ddaedalus.plugins.directory=$PLUGIN_DIR" \
    ${RUN_ARGS:+"$RUN_ARGS"}
