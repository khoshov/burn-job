package com.example.badhibernate.examples;

/**
 * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [T7]
 * Bottleneck: Static listener collection accumulating retained references
 * Original file (T7_MemoryLeakExample.java) remains COMPLETELY UNTOUCHED.
 */
public class T7_MemoryLeakExample_Variants {

    // ========================================================
    // VARIANT [v1] 🏆 [WINNER SELECTED BY KÙZODB / MAVEN]
    // ========================================================
    /*
package examples.t7_memory_leak;

import jakarta.persistence.EntityManager;
import java.util.List;
import java.util.logging.Logger;

/**
 * Candidate 1: Batch Window with Periodic Flush/Clear
 * Uses a configurable batch size and explicit flush/clear cycles.
 */
public class T7_MemoryLeakExample_Candidate1 {
    private static final Logger LOG = Logger.getLogger(T7_MemoryLeakExample_Candidate1.class.getName());
    private static final int DEFAULT_BATCH_SIZE = 50;

    public void processBulkOptimal(List<Object> entities, EntityManager em) {
        processBulkOptimal(entities, em, DEFAULT_BATCH_SIZE);
    }

    public void processBulkOptimal(List<Object> entities, EntityManager em, int batchSize) {
        if (entities == null || entities.isEmpty()) {
            return;
        }

        for (int i = 0; i < entities.size(); i++) {
            em.persist(entities.get(i));

            // Flush and clear at batch boundaries
            if ((i + 1) % batchSize == 0) {
                em.flush();
                em.clear();
                LOG.fine(() -> "Flushed and cleared at index: " + (i + 1));
            }
        }

        // Final flush for remaining entities
        em.flush();
        em.clear();
        LOG.fine("Final flush and clear completed");
    }
}
    */

    // ========================================================
    // VARIANT [v2] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t7_memory_leak;

import jakarta.persistence.EntityManager;
import jakarta.persistence.EntityTransaction;
import org.hibernate.Session;
import org.hibernate.StatelessSession;
import java.util.List;
import java.util.logging.Logger;

/**
 * Candidate 2: Transaction-Per-Batch with Stateless Session
 * Uses Hibernate's StatelessSession to avoid first-level cache entirely.
 */
public class T7_MemoryLeakExample_Candidate2 {
    private static final Logger LOG = Logger.getLogger(T7_MemoryLeakExample_Candidate2.class.getName());
    private static final int BATCH_SIZE = 50;

    public void processBulkOptimal(List<Object> entities, EntityManager em) {
        if (entities == null || entities.isEmpty()) {
            return;
        }

        // Unwrap to get Hibernate's StatelessSession
        StatelessSession statelessSession = em.unwrap(Session.class).getSessionFactory()
                .openStatelessSession();

        try {
            EntityTransaction transaction = em.getTransaction();
            transaction.begin();

            for (int i = 0; i < entities.size(); i++) {
                statelessSession.insert(entities.get(i));

                // Commit and start new transaction at batch boundaries
                if ((i + 1) % BATCH_SIZE == 0) {
                    transaction.commit();
                    LOG.fine(() -> "Committed batch at index: " + (i + 1));
                    transaction.begin();
                }
            }

            transaction.commit();
            LOG.fine("Final transaction committed");
        } catch (Exception e) {
            LOG.severe("Error during bulk processing: " + e.getMessage());
            throw e;
        } finally {
            statelessSession.close();
        }
    }
}
    */

    // ========================================================
    // VARIANT [v3] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t7_memory_leak;

import jakarta.persistence.EntityManager;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.List;
import java.util.logging.Logger;

/**
 * Candidate 3: JDBC Batch with Manual Connection Management
 * Uses raw JDBC batch operations to completely avoid Hibernate's persistence context.
 */
public class T7_MemoryLeakExample_Candidate3 {
    private static final Logger LOG = Logger.getLogger(T7_MemoryLeakExample_Candidate3.class.getName());
    private static final int BATCH_SIZE = 100;

    public void processBulkOptimal(List<Object> entities, EntityManager em) {
        if (entities == null || entities.isEmpty()) {
            return;
        }

        // Get underlying JDBC connection
        Connection connection = em.unwrap(Session.class).doReturningWork(work -> work);

        try {
            connection.setAutoCommit(false);

            // This is a simplified example - in real code you'd need to determine
            // the actual table and columns dynamically
            String sql = "INSERT INTO your_table (id, data) VALUES (?, ?)";
            try (PreparedStatement ps = connection.prepareStatement(sql)) {

                for (int i = 0; i < entities.size(); i++) {
                    // Map entity to prepared statement parameters
                    // This is simplified - real implementation needs reflection or mapping
                    ps.setObject(1, i); // Example: set ID
                    ps.setObject(2, entities.get(i).toString()); // Example: set data
                    ps.addBatch();

                    // Execute batch at intervals
                    if ((i + 1) % BATCH_SIZE == 0) {
                        ps.executeBatch();
                        connection.commit();
                        LOG.fine(() -> "Executed batch at index: " + (i + 1));
                    }
                }

                // Execute remaining batch
                ps.executeBatch();
                connection.commit();
                LOG.fine("Final batch executed and committed");
            }
        } catch (SQLException e) {
            LOG.severe("SQL error during bulk processing: " + e.getMessage());
            try {
                connection.rollback();
            } catch (SQLException rollbackEx) {
                LOG.severe("Rollback failed: " + rollbackEx.getMessage());
            }
            throw new RuntimeException("Bulk processing failed", e);
        } finally {
            try {
                connection.setAutoCommit(true);
            } catch (SQLException e) {
                LOG.warning("Failed to reset auto-commit: " + e.getMessage());
            }
        }
    }
}
    */

}
