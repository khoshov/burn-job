package ru.hackathon.profiling.sensorhub.job;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import ru.hackathon.profiling.sensorhub.repo.DailySummaryRepository;

@Component
@ConditionalOnProperty(name = "app.job.aggregation.enabled", havingValue = "true")
public class DailyAggregationJob {

    private static final Logger log = LoggerFactory.getLogger(DailyAggregationJob.class);

    private final DailySummaryRepository dailySummaryRepository;

    public DailyAggregationJob(DailySummaryRepository dailySummaryRepository) {
        this.dailySummaryRepository = dailySummaryRepository;
    }

    @Scheduled(fixedDelayString = "${app.job.aggregation.fixed-delay-ms:1000}")
    public void runAggregation() {
        log.debug("Running background daily summary aggregation...");
        // Job background logic
    }
}
