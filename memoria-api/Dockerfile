# --- dependency layer (re-runs only when pom.xml changes) ---
FROM eclipse-temurin:21-jdk-alpine AS deps
WORKDIR /build
RUN apk add --no-cache maven
COPY pom.xml .
RUN mvn dependency:go-offline -q

# --- compile + package layer (re-runs when src changes) ---
FROM deps AS build
COPY src ./src
RUN mvn package -DskipTests -q

# --- dev stage: mounts source at runtime, no image rebuild needed ---
FROM deps AS dev
EXPOSE 8084
ENTRYPOINT ["mvn", "spring-boot:run", "-Dspring-boot.run.mainClass=com.memoria.api.MemoriaApiApplication", "-Dspring-boot.run.jvmArguments=-Dspring.devtools.restart.enabled=false"]

FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app
RUN addgroup -S appgroup && adduser -S memoriauser -G appgroup
USER memoriauser
COPY --from=build --chown=memoriauser:appgroup /build/target/memoria-api.jar app.jar
ENTRYPOINT ["java", \
  "-XX:+UseContainerSupport", \
  "-XX:MaxRAMPercentage=75.0", \
  "-Djava.security.egd=file:/dev/./urandom", \
  "-jar", "app.jar"]
EXPOSE 8084
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD wget -qO- http://localhost:8084/actuator/health | grep -q UP || exit 1
