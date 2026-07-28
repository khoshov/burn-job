package examples.t3_improper_func_usage;

/**
 * 🚨 T3. Неправильное использование функций (Improper Function & Entity Usage)
 * Пример: выборка полной тяжелой сущности Entity ради проверки наличия или получения одного скаляра.
 */
public class T3_ImproperFuncUsageExample {

    public interface UserProjection {
        Long getId();
        String getEmail();
    }

    // ❌ Sub-optimal: Чтение всей сущности из БД через findById() ради проверки существования
    public boolean checkUserExistsSubOptimal(Long userId, UserRepository repo) {
        return repo.findUserById(userId) != null; // Загружает все поля сущности в PersistenceContext
    }

    // ✅ Optimal Fix (Вариант 3.2): Использование метода existsById() (SELECT COUNT(*) > 0)
    public boolean checkUserExistsOptimal(Long userId, UserRepository repo) {
        return repo.existsById(userId); // Генерирует быструю проверку на стороне СУБД
    }

    public interface UserRepository {
        Object findUserById(Long id);
        boolean existsById(Long id);
    }
}
