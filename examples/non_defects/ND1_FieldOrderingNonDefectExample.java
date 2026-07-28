package examples.non_defects;

/**
 * 🟢 Section 7 Rule 1 (ND-1): Порядок объявления полей в классе (Field Ordering)
 * 
 * Обоснование:
 * Порядок объявления полей класса в исходном коде Java НЕ влияет на объем занимаемой памяти.
 * JVM HotSpot во время загрузки класса автоматически оптимизирует раскладку полей (field reordering),
 * выравнивая 8-байтовые, 4-байтовые и 1-байтовые типы для предотвращения лишнего padding.
 * Измерение JOL (Java Object Layout) показывает идентичный размер объекта (40B).
 */
public class ND1_FieldOrderingNonDefectExample {

    // Выглядит неоптимально в коде, но HotSpot автоматически сгруппирует поля
    public static class UnorderedFields {
        byte b1;
        long l1;
        byte b2;
        long l2;
    }

    // Выглядит упорядоченно в коде
    public static class OrderedFields {
        long l1;
        long l2;
        byte b1;
        byte b2;
    }
}
