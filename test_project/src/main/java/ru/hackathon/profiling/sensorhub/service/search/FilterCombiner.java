package ru.hackathon.profiling.sensorhub.service.search;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import ru.hackathon.profiling.sensorhub.web.ApiException;
import ru.hackathon.profiling.sensorhub.web.dto.FilterPreviewDto;

import java.util.*;

@Service
public class FilterCombiner {

    public FilterPreviewDto combineFilters(List<String> filters) {
        if (filters != null && filters.size() > 8) {
            throw new ApiException("TOO_MANY_FILTERS", "Maximum of 8 filters allowed", HttpStatus.BAD_REQUEST);
        }
        if (filters == null || filters.isEmpty()) {
            return new FilterPreviewDto(Collections.emptyList(), 0);
        }

        List<String> sorted = new ArrayList<>(filters);
        Collections.sort(sorted);
        String combined = String.join("+", sorted);
        return new FilterPreviewDto(List.of(combined), 1);
    }
}
