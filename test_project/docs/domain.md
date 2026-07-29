# Domain Contract & API Documentation

## Entities
- `Station` (code, title, region, active, installedOn)
- `Measurement` (station, metricCode, measured, takenAt, qualityFlag, noteText)
- `RawSample` (stationId, metricCode, measured, takenAt, quality, payloadNote)
- `MetricType` (code, title, unitLabel, scale)
- `ImportBatch` (batchKey, fileName, rowsAccepted, rowsRejected, status, startedAt, finishedAt)
- `DailySummary` (stationId, summaryDate, samples, avgMeasured, maxMeasured)
- `AccessAudit` (path, httpMethod, statusCode, elapsedMs, loggedAt, correlationId)
