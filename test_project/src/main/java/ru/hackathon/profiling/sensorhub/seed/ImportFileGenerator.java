package ru.hackathon.profiling.sensorhub.seed;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import ru.hackathon.profiling.sensorhub.config.AppProperties;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Locale;

@Component
public class ImportFileGenerator {

    private static final Logger log = LoggerFactory.getLogger(ImportFileGenerator.class);

    private final AppProperties appProperties;

    public ImportFileGenerator(AppProperties appProperties) {
        this.appProperties = appProperties;
    }

    public void generateIfMissing() {
        try {
            Path dirPath = Paths.get(appProperties.getDataDir());
            if (!Files.exists(dirPath)) {
                Files.createDirectories(dirPath);
            }

            generateFile(dirPath.resolve("samples-500.csv"), 500);
            generateFile(dirPath.resolve("samples-50k.csv"), appProperties.getSeed().getImportRows());
        } catch (Exception e) {
            log.error("Failed to generate import CSV files", e);
        }
    }

    private void generateFile(Path path, int rows) throws Exception {
        if (Files.exists(path)) {
            return;
        }
        log.info("Generating CSV import file: {} ({} rows)", path.getFileName(), rows);
        try (BufferedWriter bw = new BufferedWriter(new FileWriter(path.toFile()))) {
            bw.write("stationCode,metricCode,measured,takenAt,quality\n");
            for (int i = 1; i <= rows; i++) {
                int stIdx = (int) (SeedFormulas.mix(i, 3) % appProperties.getSeed().getStations()) + 1;
                String stCode = SeedFormulas.stationCode(stIdx);
                String metric = SeedFormulas.metricCode(i);
                double measured = SeedFormulas.measured(i);
                String takenAt = SeedFormulas.takenAt(i).toString();
                String quality = (i % 20 == 0) ? "UNCERTAIN" : "GOOD";

                bw.write(String.format(Locale.US, "%s,%s,%.3f,%s,%s\n",
                        stCode, metric, measured, takenAt, quality));
            }
        }
    }
}
