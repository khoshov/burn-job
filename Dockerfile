# Stage 1: Build application with Maven and Java 21
FROM maven:3.9.8-eclipse-temurin-21-alpine AS builder
WORKDIR /app

COPY pom.xml .
COPY src ./src

RUN mvn clean package -DskipTests -B

# Stage 2: Minimal Java 21 Runtime Image
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

COPY --from=builder /app/target/bad-hibernate-demo-0.0.1-SNAPSHOT.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
