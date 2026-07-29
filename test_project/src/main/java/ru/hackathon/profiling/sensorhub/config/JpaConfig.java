package ru.hackathon.profiling.sensorhub.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

@Configuration
@EnableJpaRepositories(basePackages = "ru.hackathon.profiling.sensorhub.repo")
public class JpaConfig {
}
