# SPDX-License-Identifier: MIT
#
# Container image for daedalus-server.
# Multi-stage: full reactor build in a Maven image, then a slim JRE runtime
# carrying only the executable Spring Boot jar. Build from the repo root:
#
#   docker build -t daedalus-server .
#   docker run -p 8080:8080 daedalus-server

FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /workspace

# Copy poms first so dependency resolution caches as its own layer;
# source changes then don't re-download the world.
COPY pom.xml .
COPY daedalus-plugin-api/pom.xml daedalus-plugin-api/
COPY daedalus-core/pom.xml daedalus-core/
COPY daedalus-plugin-runtime/pom.xml daedalus-plugin-runtime/
COPY daedalus-server/pom.xml daedalus-server/
COPY daedalus-desktop/pom.xml daedalus-desktop/
RUN mvn -B -ntp -q dependency:go-offline || true

COPY daedalus-plugin-api daedalus-plugin-api
COPY daedalus-core daedalus-core
COPY daedalus-plugin-runtime daedalus-plugin-runtime
COPY daedalus-server daedalus-server
COPY daedalus-desktop daedalus-desktop
RUN mvn -B -ntp -DskipTests clean install

FROM eclipse-temurin:21-jre AS runtime
WORKDIR /app

RUN groupadd --system daedalus && useradd --system --gid daedalus daedalus
USER daedalus

COPY --from=build /workspace/daedalus-server/target/daedalus-server-*-exec.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
