package examples.t1_redundant_ops;

import java.util.ArrayList;
import java.util.List;

/**
 * 🚨 T1. Избыточные вычисления и операции (Redundant Computations & Operations)
 * Пример: выполнение повторных вычислений или сетевых сохранения в цикле без пакетирования.
 */
public class T1_RedundantOpsExample {

    // ❌ Sub-optimal: Поштучное сохранение в цикле (N сетевых вызовов)
    public void processSubOptimal(List<String> items) {
        for (String item : items) {
            saveSingleItemToDatabase(item); // N сетевых раундтрипов
        }
    }

    // ✅ Optimal Fix (Вариант 1.1): Накопление в пакет и единый вызов saveAll
    public void processOptimal(List<String> items) {
        List<String> batch = new ArrayList<>(items);
        saveBatchToDatabase(batch); // 1 сетевой раундтрип с JDBC Batching
    }

    private void saveSingleItemToDatabase(String item) {
        // Симуляция единичного сохранения
    }

    private void saveBatchToDatabase(List<String> items) {
        // Симуляция пакетного сохранения
    }
}
