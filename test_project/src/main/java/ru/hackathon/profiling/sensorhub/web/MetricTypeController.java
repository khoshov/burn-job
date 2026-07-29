package ru.hackathon.profiling.sensorhub.web;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import ru.hackathon.profiling.sensorhub.service.reference.MetricTypeService;
import ru.hackathon.profiling.sensorhub.web.dto.MetricTypeDto;
import ru.hackathon.profiling.sensorhub.web.dto.MetricTypeUpdateRequest;

import java.util.List;

@RestController
@RequestMapping("/api/metric-types")
public class MetricTypeController {

    private final MetricTypeService metricTypeService;

    public MetricTypeController(MetricTypeService metricTypeService) {
        this.metricTypeService = metricTypeService;
    }

    @GetMapping
    public List<MetricTypeDto> getAllMetricTypes() {
        return metricTypeService.findAll();
    }

    @PutMapping("/{code}")
    public MetricTypeDto updateMetricType(
            @PathVariable String code,
            @Valid @RequestBody MetricTypeUpdateRequest request
    ) {
        return metricTypeService.update(code, request);
    }
}
