package ru.hackathon.profiling.sensorhub.web;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.hackathon.profiling.sensorhub.service.export.CsvExportService;

import java.time.Instant;

@RestController
@RequestMapping("/api/export")
public class ExportController {

    private final CsvExportService csvExportService;

    public ExportController(CsvExportService csvExportService) {
        this.csvExportService = csvExportService;
    }

    @GetMapping("/samples.csv")
    public void exportSamplesCsv(
            @RequestParam(required = false) Instant from,
            @RequestParam(required = false) Instant to,
            @RequestParam(required = false) String metric,
            @RequestParam(required = false) Integer limit,
            HttpServletResponse response
    ) throws Exception {
        response.setContentType("text/csv; charset=UTF-8");
        response.setHeader("Content-Disposition", "attachment; filename=\"samples.csv\"");
        csvExportService.exportSamples(from, to, metric, limit, response.getWriter());
    }
}
