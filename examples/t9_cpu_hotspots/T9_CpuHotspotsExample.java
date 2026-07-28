package examples.t9_cpu_hotspots;

import java.util.List;
import java.util.regex.Pattern;

/**
 * 🚨 T9. Избыточная нагрузка на CPU (CPU Hotspots)
 * Пример: конкатенация строк в цикле и повторная компиляция регулярных выражений.
 */
public class T9_CpuHotspotsExample {

    private static final Pattern COMPILED_PATTERN = Pattern.compile("^[A-Z0-9]+$");

    // ❌ Sub-optimal: Конкатенация + в цикле и Pattern.compile на каждом шаге
    public String buildReportSubOptimal(List<String> items) {
        String result = "";
        for (String item : items) {
            if (item.matches("^[A-Z0-9]+$")) { // Повторный Pattern.compile каждый раз!
                result += item + ","; // Оператор + выделяет новые строки в Heap
            }
        }
        return result;
    }

    // ✅ Optimal Fix (Вариант 9.1 & 9.2): StringBuilder + Предкомпилированный Pattern
    public String buildReportOptimal(List<String> items) {
        StringBuilder sb = new StringBuilder(items.size() * 16);
        for (String item : items) {
            if (COMPILED_PATTERN.matcher(item).matches()) { // Предкомпилированный статический Pattern
                sb.append(item).append(","); // Избегает мусора в Heap
            }
        }
        return sb.toString();
    }
}
