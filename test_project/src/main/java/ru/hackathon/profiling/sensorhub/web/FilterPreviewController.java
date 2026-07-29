package ru.hackathon.profiling.sensorhub.web;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.hackathon.profiling.sensorhub.service.search.FilterCombiner;
import ru.hackathon.profiling.sensorhub.web.dto.FilterPreviewDto;

import java.util.List;

@RestController
@RequestMapping("/api/filters")
public class FilterPreviewController {

    private final FilterCombiner filterCombiner;

    public FilterPreviewController(FilterCombiner filterCombiner) {
        this.filterCombiner = filterCombiner;
    }

    @GetMapping("/preview")
    public FilterPreviewDto previewFilters(@RequestParam(name = "f", required = false) List<String> filters) {
        return filterCombiner.combineFilters(filters);
    }
}
