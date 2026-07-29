package ru.hackathon.profiling.sensorhub;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.scheduling.annotation.EnableScheduling;
import ru.hackathon.profiling.sensorhub.config.AppProperties;

@SpringBootApplication
@EnableScheduling
@EnableCaching
@EnableConfigurationProperties(AppProperties.class)
public class SensorHubApplication {

    public static void main(String[] args) {
        SpringApplication.run(SensorHubApplication.class, args);
    }
}
