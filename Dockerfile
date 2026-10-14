# SPDX-License-Identifier: MIT
#
# Container image for daedalus-server.
# Multi-stage: full reactor build in a Maven image, then a slim JRE runtime
# carrying only the executable Spring Boot jar. Build from the repo root:
#
#   docker build -t daedalus-server .
#   docker run -p 8080:8080 -v daedalus-data:/var/daedalus daedalus-server
#
# deploy/compose.yaml runs it for players (TLS, Redis, backups); see deploy/README.md.

FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /workspace

# Copy poms first so dependency resolution caches as its own layer;
# source changes then don't re-download the world. Every reactor module listed in pom.xml must be here.
COPY pom.xml .
COPY config config
COPY .mvn .mvn
COPY daedalus-plugin-api/pom.xml daedalus-plugin-api/
COPY daedalus-core/pom.xml daedalus-core/
COPY daedalus-wallet/pom.xml daedalus-wallet/
COPY daedalus-plugin-runtime/pom.xml daedalus-plugin-runtime/
COPY daedalus-server/pom.xml daedalus-server/
COPY daedalus-desktop/pom.xml daedalus-desktop/
COPY daedalus-explore/pom.xml daedalus-explore/
RUN mvn -B -ntp -q dependency:go-offline || true

COPY daedalus-plugin-api daedalus-plugin-api
COPY daedalus-core daedalus-core
COPY daedalus-wallet daedalus-wallet
COPY daedalus-plugin-runtime daedalus-plugin-runtime
COPY daedalus-server daedalus-server
COPY daedalus-desktop daedalus-desktop
COPY daedalus-explore daedalus-explore
# Maven resources intentionally shared with Unreal and the kennel source data.
# Omitting these directories silently creates JARs that cannot initialize the server.
COPY engines/unreal/DaedalusLink/Content/Inventory engines/unreal/DaedalusLink/Content/Inventory
COPY tools/islands/kennel-isle/tonics.json tools/islands/kennel-isle/tonics.json
# Only the server and what it needs: the desktop and explore apps aren't in the image.
RUN mvn -B -ntp -DskipTests -pl daedalus-server -am clean install

FROM eclipse-temurin:21-jre AS runtime
WORKDIR /app

RUN groupadd --system daedalus && useradd --system --gid daedalus daedalus \
    && mkdir -p /var/daedalus/world /var/daedalus/plugins \
    && chown -R daedalus:daedalus /var/daedalus

COPY --from=build /workspace/daedalus-server/target/daedalus-server-*-exec.jar app.jar

USER daedalus

# Everything a player changes lives on this volume: worlds, gates, fleets, deeds (back it up; deploy/backup.sh).
ENV DAEDALUS_WORLD_FILE=/var/daedalus/world/world-zero.daew \
    DAEDALUS_PLUGIN_DIR=/var/daedalus/plugins \
    JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError"
VOLUME ["/var/daedalus"]

EXPOSE 8080
# bash /dev/tcp: no curl needed in the JRE image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/8080 && printf "GET /actuator/health HTTP/1.0\r\nHost: localhost\r\n\r\n" >&3 && grep -q "\"UP\"" <&3'
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
