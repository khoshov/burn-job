package examples.non_defects;

import java.util.ArrayList;
import java.util.List;

/**
 * 🟢 Section 7 Rule 6 (ND-6): Стиль кода, не влияющий на поведение и затраты (Code Style & Formatting)
 * 
 * Обоснование:
 * Выбор стиля написания (традиционный цикл `for` против `Stream API`, переносы строк,
 * порядок методов в файле или длинные имена переменных) при одинаковой алгоритмической сложности
 * компилируется в эквивалентный байт-код с нулевым давлением на память и процессоры,
 * и НЕ является дефектом производительности.
 */
public class ND6_CodeStyleFormattingNonDefectExample {

    // Стиль A: Традиционный цикл for-each
    public List<String> toUpperCaseLoop(List<String> input) {
        List<String> result = new ArrayList<>(input.size());
        for (String item : input) {
            result.add(item.toUpperCase());
        }
        return result;
    }

    // Стиль B: Stream API map
    public List<String> toUpperCaseStream(List<String> input) {
        return input.stream().map(String::toUpperCase).toList();
    }
}
