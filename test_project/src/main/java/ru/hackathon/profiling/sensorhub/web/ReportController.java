package ru.hackathon.profiling.sensorhub.web;

import org.springframework.web.bind.annotation.*;
import ru.hackathon.profiling.sensorhub.service.report.DailyReportService;
import ru.hackathon.profiling.sensorhub.service.report.SampleOverviewService;
import ru.hackathon.profiling.sensorhub.service.report.TopReportService;
import ru.hackathon.profiling.sensorhub.web.dto.DailyRowDto;
import ru.hackathon.profiling.sensorhub.web.dto.OverviewDto;
import ru.hackathon.profiling.sensorhub.web.dto.TopRowDto;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

@RestController
@RequestMapping("/api/reports")
public class ReportController {

    private final DailyReportService dailyReportService;
    private final TopReportService topReportService;
    private final SampleOverviewService sampleOverviewService;

    public ReportController(DailyReportService dailyReportService,
                            TopReportService topReportService,
                            SampleOverviewService sampleOverviewService) {
        this.dailyReportService = dailyReportService;
        this.topReportService = topReportService;
        this.sampleOverviewService = sampleOverviewService;
    }

    @GetMapping("/daily")
    public List<DailyRowDto> getDailyReport(@RequestParam LocalDate from, @RequestParam LocalDate to) {
        return dailyReportService.getDailyReport(from, to);
    }

    @GetMapping("/top")
    public List<TopRowDto> getTopReport(@RequestParam String metric, @RequestParam(defaultValue = "10") int limit) {
        return topReportService.getTop(metric, limit);
    }

    @GetMapping("/overview")
    public OverviewDto getOverview(@RequestParam(required = false) Instant from, @RequestParam(required = false) Instant to) {
        return sampleOverviewService.getOverview(from, to);
    }
}
