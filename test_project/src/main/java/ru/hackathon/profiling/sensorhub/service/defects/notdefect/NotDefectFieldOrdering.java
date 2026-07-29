package ru.hackathon.profiling.sensorhub.service.defects.notdefect;

import org.springframework.stereotype.Service;

@Service
public class NotDefectFieldOrdering {

    static class BadOrder {
        boolean flag;
        double value;
        int count;
        String label;
        long timestamp;

        BadOrder(boolean flag, double value, int count, String label, long timestamp) {
            this.flag = flag;
            this.value = value;
            this.count = count;
            this.label = label;
            this.timestamp = timestamp;
        }
    }

    static class GoodOrder {
        double value;
        long timestamp;
        int count;
        boolean flag;
        String label;

        GoodOrder(double value, long timestamp, int count, boolean flag, String label) {
            this.value = value;
            this.timestamp = timestamp;
            this.count = count;
            this.flag = flag;
            this.label = label;
        }
    }

    public String compareFieldOrder() {
        BadOrder bad = new BadOrder(true, 1.0, 42, "test", 1000L);
        GoodOrder good = new GoodOrder(1.0, 1000L, 42, true, "test");
        return bad.getClass().getDeclaredFields().length == good.getClass().getDeclaredFields().length
                ? "same-field-count" : "different-field-count";
    }

    public String describeBadOrder(boolean flag, double value, int count, String label, long timestamp) {
        BadOrder o = new BadOrder(flag, value, count, label, timestamp);
        return o.label + ":" + o.timestamp;
    }

    public String describeGoodOrder(boolean flag, double value, int count, String label, long timestamp) {
        GoodOrder o = new GoodOrder(value, timestamp, count, flag, label);
        return o.label + ":" + o.timestamp;
    }
}
