package ru.hackathon.profiling.sensorhub.service.imports;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import ru.hackathon.profiling.sensorhub.config.AppProperties;
import ru.hackathon.profiling.sensorhub.web.ApiException;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

@Component
public class ImportSourceReader {

    private final AppProperties appProperties;

    public ImportSourceReader(AppProperties appProperties) {
        this.appProperties = appProperties;
    }

    public List<String> readLines(String filename) {
        Path path = Paths.get(appProperties.getDataDir(), filename);
        if (!Files.exists(path)) {
            throw new ApiException("SOURCE_NOT_FOUND", "Import source file not found: " + filename, HttpStatus.BAD_REQUEST);
        }
        try {
            return Files.readAllLines(path);
        } catch (Exception e) {
            throw new ApiException("SOURCE_NOT_FOUND", "Error reading import source file: " + e.getMessage(), HttpStatus.BAD_REQUEST);
        }
    }
}
