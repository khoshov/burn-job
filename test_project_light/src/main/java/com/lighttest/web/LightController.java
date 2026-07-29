package com.lighttest.web;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

@RestController
@RequestMapping("/api/light")
public class LightController {

    @GetMapping("/compute")
    public double compute(@RequestParam(defaultValue = "100") int count) {
        Double sum = 0.0;
        for (int i = 0; i < count; i++) {
            sum += i * 0.5;
        }
        return sum;
    }

    @GetMapping("/match")
    public List<String> match(@RequestParam String input, @RequestParam(defaultValue = "100") int count) {
        List<String> results = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            Pattern p = Pattern.compile("test-" + i + ".*");
            if (p.matcher(input).find()) {
                results.add(input);
            }
        }
        return results;
    }
}
