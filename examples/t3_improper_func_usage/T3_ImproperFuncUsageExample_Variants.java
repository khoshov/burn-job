package com.example.badhibernate.examples;

/**
 * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [T3]
 * Bottleneck: Full entity fetch for simple existence check
 * Original file (T3_ImproperFuncUsageExample.java) remains COMPLETELY UNTOUCHED.
 */
public class T3_ImproperFuncUsageExample_Variants {

    // ========================================================
    // VARIANT [v1] 🏆 [WINNER SELECTED BY KÙZODB / MAVEN]
    // ========================================================
    /*
package examples.t3_improper_func_usage;

/**
 * T3 Fix - Candidate 1: Native SQL existence check at repository level
 * Uses a lightweight SELECT COUNT(*) query via native SQL
 */
public class T3_ImproperFuncUsageExample_Candidate1 {

    public interface UserProjection {
        Long getId();
        String getEmail();
    }

    // ✅ Optimal: Uses native SQL COUNT query - no entity loading
    public boolean checkUserExistsOptimal(Long userId, UserRepository repo) {
        return repo.existsUserByIdNative(userId);
    }

    public interface UserRepository {
        // Native SQL approach - minimal database overhead
        @Query(value = "SELECT COUNT(*) > 0 FROM users WHERE id = :userId", nativeQuery = true)
        boolean existsUserByIdNative(@Param("userId") Long userId);
        
        // Original sub-optimal method kept for reference
        Object findUserById(Long id);
    }
}
    */

    // ========================================================
    // VARIANT [v2] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t3_improper_func_usage;

/**
 * T3 Fix - Candidate 2: Projection-based existence check
 * Fetches only the ID field instead of the full entity
 */
public class T3_ImproperFuncUsageExample_Candidate2 {

    public interface UserProjection {
        Long getId();
        String getEmail();
    }

    // ✅ Optimal: Uses projection to fetch only ID - avoids full entity loading
    public boolean checkUserExistsOptimal(Long userId, UserRepository repo) {
        return repo.findUserProjectionById(userId) != null;
    }

    public interface UserRepository {
        // Projection approach - fetches only ID field
        UserProjection findUserProjectionById(Long id);
        
        // Alternative: Direct ID-only query
        @Query("SELECT u.id FROM User u WHERE u.id = :userId")
        Long findUserIdById(@Param("userId") Long userId);
        
        // Original sub-optimal method kept for reference
        Object findUserById(Long id);
    }
}
    */

    // ========================================================
    // VARIANT [v3] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t3_improper_func_usage;

import java.util.BitSet;
import java.util.concurrent.ConcurrentHashMap;

/**
 * T3 Fix - Candidate 3: Cached existence check with Bloom filter
 * Uses in-memory Bloom filter for O(1) negative checks, database for positive confirmation
 */
public class T3_ImproperFuncUsageExample_Candidate3 {

    private static final int BLOOM_FILTER_SIZE = 1000000;
    private static final int HASH_FUNCTIONS = 3;
    
    private final BitSet bloomFilter = new BitSet(BLOOM_FILTER_SIZE);
    private final ConcurrentHashMap<Long, Boolean> existenceCache = new ConcurrentHashMap<>();

    // ✅ Optimal: Bloom filter + cache for repeated existence checks
    public boolean checkUserExistsOptimal(Long userId, UserRepository repo) {
        // 1. Check cache first
        Boolean cached = existenceCache.get(userId);
        if (cached != null) {
            return cached;
        }
        
        // 2. Check Bloom filter for quick negative
        if (!bloomFilterContains(userId)) {
            existenceCache.put(userId, false);
            return false;
        }
        
        // 3. Fall back to database for positive confirmation
        boolean exists = repo.existsById(userId);
        existenceCache.put(userId, exists);
        
        // Update Bloom filter on positive result
        if (exists) {
            addToBloomFilter(userId);
        }
        
        return exists;
    }

    private boolean bloomFilterContains(Long userId) {
        long hash1 = userId.hashCode() & Integer.MAX_VALUE;
        long hash2 = (userId * 31) & Integer.MAX_VALUE;
        long hash3 = (userId * 37) & Integer.MAX_VALUE;
        
        return bloomFilter.get((int)(hash1 % BLOOM_FILTER_SIZE)) &&
               bloomFilter.get((int)(hash2 % BLOOM_FILTER_SIZE)) &&
               bloomFilter.get((int)(hash3 % BLOOM_FILTER_SIZE));
    }

    private void addToBloomFilter(Long userId) {
        long hash1 = userId.hashCode() & Integer.MAX_VALUE;
        long hash2 = (userId * 31) & Integer.MAX_VALUE;
        long hash3 = (userId * 37) & Integer.MAX_VALUE;
        
        bloomFilter.set((int)(hash1 % BLOOM_FILTER_SIZE));
        bloomFilter.set((int)(hash2 % BLOOM_FILTER_SIZE));
        bloomFilter.set((int)(hash3 % BLOOM_FILTER_SIZE));
    }

    public interface UserRepository {
        boolean existsById(Long id);
        Object findUserById(Long id);
    }
}
    */

}
