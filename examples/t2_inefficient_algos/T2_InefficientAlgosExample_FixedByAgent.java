package examples.t2_inefficient_algos;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * 🤖 RESULT OF LLM AGENT AUTOMATED CODE FIX
 * Original Defect: T2_InefficientAlgosExample.java (List.contains inside nested loop)
 * Applied Fix: Variant 2.1 (HashSet indexing O(N+M))
 * Selection Method: Multi-Variant KùzuDB Graph Evaluation (Winning Variant: v1)
 */
public class T2_InefficientAlgosExample_FixedByAgent {

    /**
     * ✅ OPTIMIZED BY AGENT:
     * Replaced O(N * M) nested List.contains search with O(N + M) HashSet lookup.
     * Performance Impact: Complexity reduced from quadratic O(N^2) to linear O(N).
     */
    public int findMatches(List<String> listA, List<String> listB) {
        if (listA == null || listB == null || listA.isEmpty() || listB.isEmpty()) {
            return 0;
        }

        // Convert lookup collection to HashSet for O(1) contains() checks
        Set<String> setB = new HashSet<>(listB);
        int matches = 0;
        for (String itemA : listA) {
            if (setB.contains(itemA)) {
                matches++;
            }
        }
        return matches;
    }
}
