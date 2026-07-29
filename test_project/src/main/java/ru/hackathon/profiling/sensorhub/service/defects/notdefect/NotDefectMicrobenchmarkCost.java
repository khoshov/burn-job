package ru.hackathon.profiling.sensorhub.service.defects.notdefect;

import org.springframework.stereotype.Service;

import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

@Service
public class NotDefectMicrobenchmarkCost {

    private static final Pattern COMPILED = Pattern.compile("^[A-Z]+$");

    public boolean validateCodeColdPath(String code) {
        if (code == null || code.length() > 8) return false;
        Pattern local = Pattern.compile("^[A-Z]{1,8}$");
        return local.matcher(code).matches();
    }

    public double formatOnce(Double value) {
        DecimalFormat df = new DecimalFormat("#0.00", DecimalFormatSymbols.getInstance(Locale.US));
        try {
            return df.parse(df.format(value)).doubleValue();
        } catch (Exception e) {
            return value;
        }
    }

    public boolean simpleEmailCheckColdPath(String email) {
        if (email == null || !email.contains("@")) return false;
        Pattern p = Pattern.compile("^.+@.+\\..+$");
        return p.matcher(email).matches();
    }

    public String trimEachInColdPath(List<String> items) {
        if (items.size() > 5) return items.get(0);
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            sb.append(s.trim()).append(",");
        }
        return sb.toString();
    }

    public String parseNumberColdPath(String raw) {
        return String.format("%.2f", Double.parseDouble(raw));
    }

    public boolean validateTokenColdPath(String token) {
        Pattern p = Pattern.compile("^[a-f0-9]{32}$");
        return p.matcher(token).matches();
    }

    public double powInColdPath(double base) {
        return Math.pow(base, 2);
    }

    public String replaceAllColdPath(String input) {
        return input.replaceAll("[\\s]+", " ").trim();
    }

    public boolean matchesColdPath(String text) {
        return COMPILED.matcher(text).matches();
    }
}
