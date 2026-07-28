package examples.t4_data_layout;

/**
 * 🚨 T4. Ошибки в раскладке данных (Data Layout & Object Overhead)
 * Пример: выгрузка тяжелых LOB-полей вместе с базовыми данными сущности.
 */
public class T4_DataLayoutExample {

    // ❌ Sub-optimal: Полнофункциональная сущность со всеми тяжелыми блобами
    public static class EmployeeFullEntity {
        private Long id;
        private String name;
        private byte[] heavyPhotoLob; // BLOB/LOB колонка (несколько мегабайт)
        private String detailedBiography; // CLOB колонка
    }

    // ✅ Optimal Fix (Вариант 4.1): Проекция только нужных полей
    public record EmployeeLightweightDto(Long id, String name) {}

    // ✅ Optimal Fix (Вариант 4.4): Вертикальное шардирование
    public static class EmployeeBase {
        private Long id;
        private String name;
        // Тяжелые поля вынесены в EmployeeDetail со связью @OneToOne(fetch = LAZY)
    }
}
