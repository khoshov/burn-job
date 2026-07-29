package ru.hackathon.profiling.sensorhub;

import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

public class ApiContractSnapshotTest extends ApiTestBase {

    @Test
    void testEndpointsExist() throws Exception {
        mockMvc.perform(MockMvcRequestBuilders.get("/api/stations"))
                .andExpect(status().isOk());

        mockMvc.perform(MockMvcRequestBuilders.get("/api/metric-types"))
                .andExpect(status().isOk());

        mockMvc.perform(MockMvcRequestBuilders.get("/api/filters/preview?f=region:URAL"))
                .andExpect(status().isOk());
    }
}
