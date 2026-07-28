package examples.t5_redundant_checks;

import java.util.List;

/**
 * 🤖 RESULT OF LLM AGENT AUTOMATED CODE FIX
 * Original Defect: T5_RedundantChecksExample.java (In-memory stream filtering after full table fetch)
 * Applied Fix: Variant 5.2 (Database SQL WHERE clause delegation)
 * Selection Method: Multi-Variant KùzuDB Graph Evaluation (Winning Variant: v1)
 */
public class T5_RedundantChecksExample_FixedByAgent {

    public interface OrderRepository {
        List<Order> findByStatus(String status);
    }

    public record Order(Long id, String status) {}

    /**
     * ✅ OPTIMIZED BY AGENT:
     * Delegated status filtering to database SQL query instead of loading full table into RAM.
     * Performance Impact: Eliminates redundant stream iteration and GC allocation pressure.
     */
    public List<Order> filterOrders(OrderRepository repository, String targetStatus) {
        // SQL query: SELECT o FROM Order o WHERE o.status = :targetStatus
        return repository.findByStatus(targetStatus);
    }
}
