import jdk.jfr.consumer.RecordedEvent;
import jdk.jfr.consumer.RecordedFrame;
import jdk.jfr.consumer.RecordedMethod;
import jdk.jfr.consumer.RecordedObject;
import jdk.jfr.consumer.RecordedStackTrace;
import jdk.jfr.consumer.RecordingFile;

import java.io.PrintStream;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

public class JfrDump {

    private static final Set<String> WANTED_EVENTS = Set.of(
            "jdk.ExecutionSample",
            "jdk.NativeMethodSample",
            "jdk.ObjectAllocationSample",
            "jdk.OldObjectSample",
            "jdk.JavaMonitorEnter",
            "jdk.ThreadPark"
    );

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: JfrDump <path-to-jfr>");
            System.exit(1);
        }
        Path path = Paths.get(args[0]);
        PrintStream out = System.out;

        try (RecordingFile rf = new RecordingFile(path)) {
            while (rf.hasMoreEvents()) {
                RecordedEvent event = rf.readEvent();
                String type = event.getEventType().getName();
                if (!WANTED_EVENTS.contains(type)) {
                    continue;
                }
                StringBuilder json = new StringBuilder();
                json.append("{\"eventType\":").append(quote(type));

                List<String> stack = extractStack(event);
                json.append(",\"stack\":[");
                for (int i = 0; i < stack.size(); i++) {
                    if (i > 0) json.append(",");
                    json.append(quote(stack.get(i)));
                }
                json.append("]");

                switch (type) {
                    case "jdk.ObjectAllocationSample" -> {
                        json.append(",\"objectClass\":").append(quote(safeClassName(event, "objectClass")));
                        json.append(",\"weight\":").append(safeLong(event, "weight", 0));
                    }
                    case "jdk.OldObjectSample" -> {
                        json.append(",\"objectClass\":").append(quote(safeObjectClassName(event, "object")));
                        json.append(",\"ageMs\":").append(safeDurationMs(event, "objectAge"));
                    }
                    case "jdk.JavaMonitorEnter" -> {
                        json.append(",\"monitorClass\":").append(quote(safeClassName(event, "monitorClass")));
                        json.append(",\"durationMs\":").append(event.getDuration().toMillis());
                    }
                    case "jdk.ThreadPark" -> {
                        json.append(",\"parkedClass\":").append(quote(safeClassName(event, "parkedClass")));
                        json.append(",\"durationMs\":").append(event.getDuration().toMillis());
                    }
                    default -> { /* jdk.ExecutionSample / jdk.NativeMethodSample: no extra fields */ }
                }
                json.append("}");
                out.println(json);
            }
        }
    }

    private static List<String> extractStack(RecordedEvent event) {
        if (!event.hasField("stackTrace")) return List.of();
        RecordedStackTrace trace = event.getStackTrace();
        if (trace == null) return List.of();
        List<RecordedFrame> frames = trace.getFrames();
        List<String> result = new ArrayList<>();
        // JFR orders frames leaf-first; reverse to root-first (matches async-profiler collapsed convention).
        for (int i = frames.size() - 1; i >= 0; i--) {
            RecordedMethod m = frames.get(i).getMethod();
            if (m == null) continue;
            String className = m.getType() != null ? m.getType().getName() : "Global";
            String methodName = m.getName() != null ? m.getName() : "unknown";
            result.add(className.replace('.', '/') + "." + methodName);
        }
        return result;
    }

    private static String safeClassName(RecordedEvent event, String field) {
        if (!event.hasField(field)) return "Unknown";
        Object value = event.getValue(field);
        if (value instanceof jdk.jfr.consumer.RecordedClass rc) {
            return rc.getName().replace('.', '/');
        }
        return "Unknown";
    }

    private static String safeObjectClassName(RecordedEvent event, String field) {
        if (!event.hasField(field)) return "Unknown";
        Object value = event.getValue(field);
        if (value instanceof RecordedObject ro && ro.hasField("type")) {
            Object type = ro.getValue("type");
            if (type instanceof jdk.jfr.consumer.RecordedClass rc) {
                return rc.getName().replace('.', '/');
            }
        }
        return "Unknown";
    }

    private static long safeLong(RecordedEvent event, String field, long fallback) {
        if (!event.hasField(field)) return fallback;
        try {
            return event.getLong(field);
        } catch (Exception e) {
            return fallback;
        }
    }

    private static long safeDurationMs(RecordedEvent event, String field) {
        if (!event.hasField(field)) return 0;
        try {
            return event.getDuration(field).toMillis();
        } catch (Exception e) {
            return 0;
        }
    }

    private static String quote(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> {
                    if (c < 0x20) sb.append(String.format("\\u%04x", (int) c));
                    else sb.append(c);
                }
            }
        }
        return sb.append('"').toString();
    }
}
