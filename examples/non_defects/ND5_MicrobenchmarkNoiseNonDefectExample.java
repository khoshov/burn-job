package examples.non_defects;

/**
 * 🟢 Section 7 Rule 5 (ND-5): Стоимость, измеримая только в синтетическом микробенчмарке (Microbenchmark Noise)
 * 
 * Обоснование:
 * Мелкие операции (например, редкая вызов `Math.sqrt` вместо математической аппроксимации
 * или редкая компиляция разового регулярного выражения), суммарная доля которых в профайле составляет < 0.5%
 * и полностью перекрывается временем сетевого ввода-вывода (I/O) СУБД, считаются шумом микробенчмарка
 * и НЕ являются дефектом производительности.
 */
public class ND5_MicrobenchmarkNoiseNonDefectExample {

    public double calculateDistanceNonDefect(double x1, double y1, double x2, double y2) {
        double dx = x2 - x1;
        double dy = y2 - y1;
        // Наносекундный вызов Math.sqrt в бизнес-методе — шум микробенчмарка (Non-Defect)
        return Math.sqrt(dx * dx + dy * dy);
    }
}
