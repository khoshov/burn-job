package ru.hackathon.profiling.sensorhub.web;

import org.springframework.http.HttpStatus;

public class StationNotFoundException extends ApiException {
    public StationNotFoundException(String code) {
        super("STATION_NOT_FOUND", "Station " + code + " not found", HttpStatus.NOT_FOUND);
    }
}
