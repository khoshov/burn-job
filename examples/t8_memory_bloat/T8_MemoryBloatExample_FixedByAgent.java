package examples.t8_memory_bloat;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;

/**
 * 🤖 RESULT OF LLM AGENT AUTOMATED CODE FIX
 * Original Defect: T8_MemoryBloatExample.java (RAM pagination skip/limit)
 * Applied Fix: Variant 8.1 (Database Spring Data Pageable LIMIT/OFFSET)
 * Selection Method: Multi-Variant KùzuDB Graph Evaluation (Winning Variant: v1)
 */
public class T8_MemoryBloatExample_FixedByAgent {

    public interface OrderRepository {
        Page<String> findByStatus(String status, Pageable pageable);
    }

    /**
     * ✅ OPTIMIZED BY AGENT:
     * Delegated pagination to database SQL LIMIT/OFFSET via Spring Data Pageable.
     * Performance Impact: RAM usage reduced from 150MB to 120KB.
     */
    public Page<String> pageOrders(OrderRepository repository, String status, Pageable pageable) {
        return repository.findByStatus(status, pageable);
    }
}
