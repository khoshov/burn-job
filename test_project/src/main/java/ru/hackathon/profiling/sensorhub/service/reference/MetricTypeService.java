package ru.hackathon.profiling.sensorhub.service.reference;

import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.hackathon.profiling.sensorhub.domain.MetricType;
import ru.hackathon.profiling.sensorhub.repo.MetricTypeRepository;
import ru.hackathon.profiling.sensorhub.web.MetricTypeNotFoundException;
import ru.hackathon.profiling.sensorhub.web.dto.MetricTypeDto;
import ru.hackathon.profiling.sensorhub.web.dto.MetricTypeUpdateRequest;

import java.util.List;

@Service
public class MetricTypeService {

    private final MetricTypeRepository metricTypeRepository;
    private final MetricTypeRegistry registry;

    public MetricTypeService(MetricTypeRepository metricTypeRepository, MetricTypeRegistry registry) {
        this.metricTypeRepository = metricTypeRepository;
        this.registry = registry;
    }

    @Transactional(readOnly = true)
    public List<MetricTypeDto> findAll() {
        return metricTypeRepository.findAll().stream()
                .map(m -> new MetricTypeDto(m.getCode(), m.getTitle(), m.getUnitLabel(), m.getScale()))
                .toList();
    }

    @Transactional
    public MetricTypeDto update(String code, MetricTypeUpdateRequest request) {
        MetricType mt = metricTypeRepository.findById(code)
                .orElseThrow(() -> new MetricTypeNotFoundException(code));
        mt.setTitle(request.title());
        mt.setUnitLabel(request.unitLabel());
        mt.setScale(request.scale());
        MetricType saved = metricTypeRepository.save(mt);
        registry.register(saved);
        return new MetricTypeDto(saved.getCode(), saved.getTitle(), saved.getUnitLabel(), saved.getScale());
    }
}
