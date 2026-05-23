FROM eclipse-temurin:21-jdk-alpine AS build
WORKDIR /build
COPY pom.xml .
COPY src ./src
RUN apk add --no-cache maven && \
    mvn dependency:go-offline -q && \
    mvn package -DskipTests -q

FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
COPY --from=build --chown=appuser:appgroup /build/target/ai-architect-api.jar app.jar
ENTRYPOINT ["java", \
  "-XX:+UseContainerSupport", \
  "-XX:MaxRAMPercentage=75.0", \
  "-Djava.security.egd=file:/dev/./urandom", \
  "-jar", "app.jar"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD wget -qO- http://localhost:8080/actuator/health | grep -q UP || exit 1
