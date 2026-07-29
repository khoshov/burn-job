package ru.hackathon.profiling.sensorhub.seed;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import ru.hackathon.profiling.sensorhub.config.AppProperties;
import ru.hackathon.profiling.sensorhub.domain.MetricType;
import ru.hackathon.profiling.sensorhub.repo.MetricTypeRepository;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.service.reference.MetricTypeRegistry;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.Timestamp;
import java.util.HexFormat;

@Component
public class SeedRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(SeedRunner.class);

    private final AppProperties appProperties;
    private final StationRepository stationRepository;
    private final MetricTypeRepository metricTypeRepository;
    private final MetricTypeRegistry metricTypeRegistry;
    private final DataSource dataSource;
    private final ImportFileGenerator importFileGenerator;

    public SeedRunner(AppProperties appProperties,
                      StationRepository stationRepository,
                      MetricTypeRepository metricTypeRepository,
                      MetricTypeRegistry metricTypeRegistry,
                      DataSource dataSource,
                      ImportFileGenerator importFileGenerator) {
        this.appProperties = appProperties;
        this.stationRepository = stationRepository;
        this.metricTypeRepository = metricTypeRepository;
        this.metricTypeRegistry = metricTypeRegistry;
        this.dataSource = dataSource;
        this.importFileGenerator = importFileGenerator;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        seedMetricTypes();
        importFileGenerator.generateIfMissing();

        if (!appProperties.getSeed().isEnabled()) {
            log.info("Seed is disabled via app.seed.enabled=false");
            return;
        }

        int targetStations = appProperties.getSeed().getStations();
        if (stationRepository.count() >= targetStations) {
            log.info("Seed skipped: station count satisfies target {}", targetStations);
            return;
        }

        log.info("Starting deterministic database seed...");
        long checksum = 0L;

        // Seed Stations
        try (Connection conn = dataSource.getConnection()) {
            conn.setAutoCommit(false);
            String sql = "INSERT INTO station (id, code, title, region, active, installed_on) VALUES (?, ?, ?, ?, ?, ?)";
            try (PreparedStatement ps = conn.prepareStatement(sql)) {
                for (int i = 1; i <= targetStations; i++) {
                    long stId = SeedFormulas.stationId(i);
                    String code = SeedFormulas.stationCode(i);
                    String title = "Station " + i;
                    String region = (i % 3 == 0) ? "SIBERIA" : (i % 2 == 0 ? "URAL" : "CENTRAL");
                    boolean active = (i % 10 != 0);

                    ps.setLong(1, stId);
                    ps.setString(2, code);
                    ps.setString(3, title);
                    ps.setString(4, region);
                    ps.setBoolean(5, active);
                    ps.setDate(6, java.sql.Date.valueOf(SeedFormulas.installedOn(i)));
                    ps.addBatch();

                    checksum ^= stId ^ code.hashCode();

                    if (i % 1000 == 0 || i == targetStations) {
                        ps.executeBatch();
                        conn.commit();
                    }
                }
            }

            // Seed Measurements
            int measPerStation = appProperties.getSeed().getMeasurementsPerStation();
            int totalMeas = targetStations * measPerStation;
            String measSql = "INSERT INTO measurement (station_id, metric_code, measured, taken_at, quality_flag, note_text) VALUES (?, ?, ?, ?, ?, ?)";
            try (PreparedStatement ps = conn.prepareStatement(measSql)) {
                int count = 0;
                for (int i = 1; i <= targetStations; i++) {
                    long stId = SeedFormulas.stationId(i);
                    for (int m = 1; m <= measPerStation; m++) {
                        count++;
                        String metric = SeedFormulas.metricCode(count);
                        double val = SeedFormulas.measured(count);
                        Timestamp takenAt = Timestamp.from(SeedFormulas.takenAt(count));

                        ps.setLong(1, stId);
                        ps.setString(2, metric);
                        ps.setDouble(3, val);
                        ps.setTimestamp(4, takenAt);
                        ps.setInt(5, 1);
                        ps.setString(6, "Seed measurement");
                        ps.addBatch();

                        checksum ^= count ^ (long) val;

                        if (count % 1000 == 0 || count == totalMeas) {
                            ps.executeBatch();
                            conn.commit();
                        }
                    }
                }
            }

            // Seed RawSamples
            int rawTarget = appProperties.getSeed().getRawSamples();
            String rawSql = "INSERT INTO raw_sample (station_id, metric_code, measured, taken_at, quality, payload_note) VALUES (?, ?, ?, ?, ?, ?)";
            try (PreparedStatement ps = conn.prepareStatement(rawSql)) {
                for (int i = 1; i <= rawTarget; i++) {
                    int stIdx = (int) (SeedFormulas.mix(i, 5) % targetStations) + 1;
                    long stId = SeedFormulas.stationId(stIdx);
                    String metric = SeedFormulas.metricCode(i);
                    double val = SeedFormulas.measured(i);
                    Timestamp takenAt = Timestamp.from(SeedFormulas.takenAt(i));
                    String quality = (i % 15 == 0) ? "UNCERTAIN" : "GOOD";

                    ps.setLong(1, stId);
                    ps.setString(2, metric);
                    ps.setDouble(3, val);
                    ps.setTimestamp(4, takenAt);
                    ps.setString(5, quality);
                    ps.setString(6, "Raw sample seed");
                    ps.addBatch();

                    checksum ^= (i * 31L) ^ (long) val;

                    if (i % 1000 == 0 || i == rawTarget) {
                        ps.executeBatch();
                        conn.commit();
                    }
                }
            }
        }

        String hexChecksum = String.format("0x%08x", (int) checksum);
        log.info("seed: stations={} measurements={} rawSamples={} metricTypes=12 importRows={} checksum={}",
                targetStations,
                targetStations * appProperties.getSeed().getMeasurementsPerStation(),
                appProperties.getSeed().getRawSamples(),
                appProperties.getSeed().getImportRows(),
                hexChecksum);
    }

    private void seedMetricTypes() {
        String[][] types = {
                {"TEMP", "Temperature", "C", "2"},
                {"HUMID", "Humidity", "%", "1"},
                {"PRESS", "Pressure", "hPa", "1"},
                {"WIND", "Wind Speed", "m/s", "2"},
                {"RAIN", "Precipitation", "mm", "2"},
                {"DUST", "Particulate Matter", "ug/m3", "1"},
                {"CO2", "Carbon Dioxide", "ppm", "0"},
                {"NOISE", "Sound Level", "dB", "1"},
                {"LUX", "Illuminance", "lx", "0"},
                {"VOLT", "Voltage", "V", "2"},
                {"AMP", "Current", "A", "2"},
                {"FLOW", "Water Flow", "L/min", "2"}
        };

        for (String[] t : types) {
            MetricType mt = new MetricType(t[0], t[1], t[2], Integer.parseInt(t[3]));
            metricTypeRepository.save(mt);
            metricTypeRegistry.register(mt);
        }
    }
}
