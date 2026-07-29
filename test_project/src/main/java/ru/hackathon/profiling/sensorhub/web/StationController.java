package ru.hackathon.profiling.sensorhub.web;

import jakarta.validation.Valid;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.hackathon.profiling.sensorhub.domain.Station;
import ru.hackathon.profiling.sensorhub.repo.StationRepository;
import ru.hackathon.profiling.sensorhub.service.search.StationStatsService;
import ru.hackathon.profiling.sensorhub.web.dto.StationCreateRequest;
import ru.hackathon.profiling.sensorhub.web.dto.StationDto;
import ru.hackathon.profiling.sensorhub.web.dto.StationStatsDto;

import java.time.LocalDate;

@RestController
@RequestMapping("/api/stations")
public class StationController {

    private final StationRepository stationRepository;
    private final StationStatsService stationStatsService;

    public StationController(StationRepository stationRepository, StationStatsService stationStatsService) {
        this.stationRepository = stationRepository;
        this.stationStatsService = stationStatsService;
    }

    @GetMapping
    public Page<StationDto> getStations(
            @RequestParam(required = false) String query,
            @RequestParam(required = false) String region,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(defaultValue = "code,asc") String sort
    ) {
        int effectiveSize = Math.min(size, 500);
        String[] sortParts = sort.split(",");
        Sort.Direction direction = sortParts.length > 1 && sortParts[1].equalsIgnoreCase("desc")
                ? Sort.Direction.DESC : Sort.Direction.ASC;
        Pageable pageable = PageRequest.of(page, effectiveSize, Sort.by(direction, sortParts[0]));

        Page<Station> stations = stationRepository.searchStations(query, region, pageable);
        return stations.map(s -> new StationDto(s.getCode(), s.getTitle(), s.getRegion(), s.isActive(), s.getInstalledOn()));
    }

    @GetMapping("/{code}")
    public StationDto getStationByCode(@PathVariable String code) {
        Station station = stationRepository.findByCodeIgnoreCase(code)
                .orElseThrow(() -> new StationNotFoundException(code));
        return new StationDto(station.getCode(), station.getTitle(), station.getRegion(), station.isActive(), station.getInstalledOn());
    }

    @GetMapping("/{code}/stats")
    public StationStatsDto getStationStats(
            @PathVariable String code,
            @RequestParam LocalDate from,
            @RequestParam LocalDate to
    ) {
        return stationStatsService.getStats(code, from, to);
    }

    @PostMapping
    public ResponseEntity<StationDto> createStation(@Valid @RequestBody StationCreateRequest request) {
        if (stationRepository.existsByCode(request.code())) {
            throw new ApiException("VALIDATION_FAILED", "Station with code " + request.code() + " already exists", HttpStatus.BAD_REQUEST);
        }
        Long id = System.currentTimeMillis();
        Station station = new Station(id, request.code(), request.title(), request.region(), true, request.installedOn());
        Station saved = stationRepository.save(station);
        StationDto dto = new StationDto(saved.getCode(), saved.getTitle(), saved.getRegion(), saved.isActive(), saved.getInstalledOn());
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }
}
