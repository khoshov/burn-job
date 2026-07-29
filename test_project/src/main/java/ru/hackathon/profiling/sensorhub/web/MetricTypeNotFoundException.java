package ru.hackathon.profiling.sensorhub.web;

import org.springframework.http.HttpStatus;

public class MetricTypeNotFoundException extends ApiException {
    public MetricTypeNotFoundException(String code) {
        super("METRIC_TYPE_NOT_FOUND", "Metric type " + code + " not found", HttpStatus.NOT_FOUND);
    }
}
