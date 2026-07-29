package ru.hackathon.profiling.sensorhub;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

public class StationControllerTest extends ApiTestBase {

    @Test
    void testGetStations() throws Exception {
        mockMvc.perform(MockMvcRequestBuilders.get("/api/stations"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").exists());
    }

    @Test
    void testGetStationNotFound() throws Exception {
        mockMvc.perform(MockMvcRequestBuilders.get("/api/stations/ST-999999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("STATION_NOT_FOUND"));
    }
}
