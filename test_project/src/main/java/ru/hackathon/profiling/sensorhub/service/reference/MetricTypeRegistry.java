package ru.hackathon.profiling.sensorhub.service.reference;

import org.springframework.stereotype.Component;
import ru.hackathon.profiling.sensorhub.domain.MetricType;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class MetricTypeRegistry {

    private final Map<String, MetricType> registry = new ConcurrentHashMap<>();

    public void register(MetricType type) {
        registry.put(type.getCode(), type);
    }

    public MetricType get(String code) {
        return registry.get(code);
    }

    public boolean contains(String code) {
        return registry.containsKey(code);
    }

    public Map<String, MetricType> getAll() {
        return registry;
    }
}
