# Coding Standards for sensorhub

- Java 21 features (Records for DTOs, Pattern Matching, Switch Expressions).
- No Lombok.
- Immutable DTOs via Records.
- Spring Data JPA with `spring.jpa.open-in-view=false`.
- Clean error responses with ErrorDto and `X-Correlation-Id`.
