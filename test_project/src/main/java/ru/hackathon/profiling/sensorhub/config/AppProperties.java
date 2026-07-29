package ru.hackathon.profiling.sensorhub.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private String dataDir = "data/imports";
    private Seed seed = new Seed();
    private Job job = new Job();
    private Limits limits = new Limits();
    private Leak leak = new Leak();

    public String getDataDir() { return dataDir; }
    public void setDataDir(String dataDir) { this.dataDir = dataDir; }

    public Seed getSeed() { return seed; }
    public void setSeed(Seed seed) { this.seed = seed; }

    public Job getJob() { return job; }
    public void setJob(Job job) { this.job = job; }

    public Limits getLimits() { return limits; }
    public void setLimits(Limits limits) { this.limits = limits; }

    public Leak getLeak() { return leak; }
    public void setLeak(Leak leak) { this.leak = leak; }

    public static class Seed {
        private boolean enabled = true;
        private int stations = 2000;
        private int measurementsPerStation = 5;
        private int rawSamples = 300000;
        private int metricTypes = 12;
        private int importRows = 50000;

        public boolean isEnabled() { return enabled; }
        public void setEnabled(boolean enabled) { this.enabled = enabled; }

        public int getStations() { return stations; }
        public void setStations(int stations) { this.stations = stations; }

        public int getMeasurementsPerStation() { return measurementsPerStation; }
        public void setMeasurementsPerStation(int measurementsPerStation) { this.measurementsPerStation = measurementsPerStation; }

        public int getRawSamples() { return rawSamples; }
        public void setRawSamples(int rawSamples) { this.rawSamples = rawSamples; }

        public int getMetricTypes() { return metricTypes; }
        public void setMetricTypes(int metricTypes) { this.metricTypes = metricTypes; }

        public int getImportRows() { return importRows; }
        public void setImportRows(int importRows) { this.importRows = importRows; }
    }

    public static class Job {
        private Aggregation aggregation = new Aggregation();

        public Aggregation getAggregation() { return aggregation; }
        public void setAggregation(Aggregation aggregation) { this.aggregation = aggregation; }

        public static class Aggregation {
            private boolean enabled = false;
            private long fixedDelayMs = 1000;

            public boolean isEnabled() { return enabled; }
            public void setEnabled(boolean enabled) { this.enabled = enabled; }

            public long getFixedDelayMs() { return fixedDelayMs; }
            public void setFixedDelayMs(long fixedDelayMs) { this.fixedDelayMs = fixedDelayMs; }
        }
    }

    public static class Limits {
        private int exportMaxRows = 300000;
        private int exportDefaultRows = 20000;
        private int importMaxRows = 200000;
        private int pageMaxSize = 500;
        private int auditWindow = 100;
        private int topMaxLimit = 100;
        private int filtersMax = 8;

        public int getExportMaxRows() { return exportMaxRows; }
        public void setExportMaxRows(int exportMaxRows) { this.exportMaxRows = exportMaxRows; }

        public int getExportDefaultRows() { return exportDefaultRows; }
        public void setExportDefaultRows(int exportDefaultRows) { this.exportDefaultRows = exportDefaultRows; }

        public int getImportMaxRows() { return importMaxRows; }
        public void setImportMaxRows(int importMaxRows) { this.importMaxRows = importMaxRows; }

        public int getPageMaxSize() { return pageMaxSize; }
        public void setPageMaxSize(int pageMaxSize) { this.pageMaxSize = pageMaxSize; }

        public int getAuditWindow() { return auditWindow; }
        public void setAuditWindow(int auditWindow) { this.auditWindow = auditWindow; }

        public int getTopMaxLimit() { return topMaxLimit; }
        public void setTopMaxLimit(int topMaxLimit) { this.topMaxLimit = topMaxLimit; }

        public int getFiltersMax() { return filtersMax; }
        public void setFiltersMax(int filtersMax) { this.filtersMax = filtersMax; }
    }

    public static class Leak {
        private int payloadBytes = 8192;

        public int getPayloadBytes() { return payloadBytes; }
        public void setPayloadBytes(int payloadBytes) { this.payloadBytes = payloadBytes; }
    }
}
