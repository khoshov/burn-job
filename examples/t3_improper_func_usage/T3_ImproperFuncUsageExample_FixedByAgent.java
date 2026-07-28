package examples.t3_improper_func_usage;

/**
 * 🤖 RESULT OF LLM AGENT AUTOMATED CODE FIX
 * Original Defect: T3_ImproperFuncUsageExample.java (Full entity fetch for existence check)
 * Applied Fix: Variant 3.2 (Spring Data existsById SELECT COUNT(*) > 0)
 * Selection Method: Multi-Variant KùzuDB Graph Evaluation (Winning Variant: v1)
 */
public class T3_ImproperFuncUsageExample_FixedByAgent {

    public interface UserRepository {
        boolean existsById(Long id);
    }

    /**
     * ✅ OPTIMIZED BY AGENT:
     * Replaced findUserById() full entity payload load with existsById() count check.
     * Performance Impact: Prevents loading LOBs and entity state into PersistenceContext.
     */
    public boolean checkUserExists(Long userId, UserRepository repo) {
        if (userId == null || repo == null) {
            return false;
        }

        // Direct SQL EXISTS check via database engine
        return repo.existsById(userId);
    }
}
