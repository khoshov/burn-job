package examples.t2_inefficient_algos;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 🚨 T2. Неэффективные алгоритмы (Inefficient Algorithms)
 * Пример: вложенные циклы поиска O(N^2) вместо использования Hash-таблиц O(N).
 */
public class T2_InefficientAlgosExample {

    // ❌ Sub-optimal: Вложенный цикл O(N * M) с поиском List.contains()
    public int findMatchesSubOptimal(List<String> listA, List<String> listB) {
        int matches = 0;
        for (String itemA : listA) {
            if (listB.contains(itemA)) { // Линейный поиск O(M) на каждом шаге
                matches++;
            }
        }
        return matches;
    }

    // ✅ Optimal Fix (Вариант 2.1): Использование HashSet для O(N + M)
    public int findMatchesOptimal(List<String> listA, List<String> listB) {
        Set<String> setB = new HashSet<>(listB); // Инициализация за O(M)
        int matches = 0;
        for (String itemA : listA) {
            if (setB.contains(itemA)) { // Поиск за O(1)
                matches++;
            }
        }
        return matches;
    }
}
