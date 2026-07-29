package ru.hackathon.profiling.sensorhub.service.defects.notdefect;

import org.springframework.stereotype.Service;

@Service
public class NotDefectStyleOnly {

    public String allmanBrace(String input) 
    {
        if (input == null) 
        {
            return "";
        }
        return input.trim();
    }

    public String kAndRBrace(String input) {
        if (input == null) {
            return "";
        }
        return input.trim();
    }

    public String
    longLineMethod(
        String first,
        String second,
        String third
    ) {
        return first + second + third;
    }

    public String shortLineMethod(String a, String b, String c) {
        return a + b + c;
    }

    static class FieldsBottom {
        String name;
        int count;
        FieldsBottom(String n, int c) { this.name = n; this.count = c; }
        String format() { return name + ":" + count; }
    }

    static class FieldsTop {
        FieldsTop(String n, int c) { this.name = n; this.count = c; }
        String format() { return name + ":" + count; }
        private String name;
        private int count;
    }

    public String styleVariant(String val, boolean flag) {
        if (flag)
            return val;
        else
            return val.toUpperCase();
    }

    public String styleVariantCompact(String val, boolean flag) {
        return flag ? val : val.toUpperCase();
    }

    public int methodOrder1() { return 1; }
    public int methodOrder2() { return 2; }
    public int methodOrder3() { return 3; }

    public String describeStyle() {
        FieldsBottom fb = new FieldsBottom("bottom", 1);
        FieldsTop ft = new FieldsTop("top", 2);
        return fb.format() + "|" + ft.format();
    }
}
