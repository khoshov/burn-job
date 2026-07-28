package examples.t7_memory_leak;

import jakarta.persistence.EntityManager;
import java.util.List;

/**
 * 🤖 RESULT OF LLM AGENT AUTOMATED CODE FIX
 * Original Defect: T7_MemoryLeakExample.java (PersistenceContext memory accumulation)
 * Applied Fix: Variant 7.1 (Batch flush & clear / Session cleanup)
 * Selection Method: Multi-Variant KùzuDB Graph Evaluation (Winning Variant: v1)
 */
public class T7_MemoryLeakExample_FixedByAgent {

    private static final int BATCH_SIZE = 50;

    /**
     * ✅ OPTIMIZED BY AGENT:
     * Added periodic flush() and clear() calls to prevent unbounded 1st level cache memory growth.
     * Performance Impact: Prevents OutOfMemoryError during bulk insertion of 100k+ records.
     */
    public void processBulk(List<Object> entities, EntityManager em) {
        if (entities == null || em == null) {
            return;
        }

        for (int i = 0; i < entities.size(); i++) {
            em.persist(entities.get(i));
            if (i > 0 && i % BATCH_SIZE == 0) {
                em.flush();
                em.clear(); // Releases managed entity references for GC
            }
        }
        em.flush();
        em.clear();
    }
}
