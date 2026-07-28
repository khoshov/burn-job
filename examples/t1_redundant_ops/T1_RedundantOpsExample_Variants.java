package com.example.badhibernate.examples;

/**
 * ALL GENERATED REFACTORING VARIANTS FOR TAXONOMY [T1]
 * Bottleneck: Unbatched save() in loop without JDBC batching
 * Original file (T1_RedundantOpsExample.java) remains COMPLETELY UNTOUCHED.
 */
public class T1_RedundantOpsExample_Variants {

    // ========================================================
    // VARIANT [v1] 🏆 [WINNER SELECTED BY KÙZODB / MAVEN]
    // ========================================================
    /*
package examples.t1_redundant_ops;

import java.util.ArrayList;
import java.util.List;

/**
 * 🚀 Variant 1: Chunked Batch Processing
 * Processes items in configurable batch sizes to balance memory and network efficiency.
 */
public class T1_RedundantOpsExample_V1 {

    private static final int DEFAULT_BATCH_SIZE = 100;

    // ✅ Optimal: Chunked batch processing
    public void processOptimal(List<String> items) {
        processOptimal(items, DEFAULT_BATCH_SIZE);
    }

    public void processOptimal(List<String> items, int batchSize) {
        if (items == null || items.isEmpty()) return;
        
        List<String> batch = new ArrayList<>(batchSize);
        for (String item : items) {
            batch.add(item);
            if (batch.size() >= batchSize) {
                saveBatchToDatabase(batch);
                batch.clear();
            }
        }
        // Save remaining items
        if (!batch.isEmpty()) {
            saveBatchToDatabase(batch);
        }
    }

    private void saveBatchToDatabase(List<String> items) {
        // Simulated batch save with JDBC batching
    }
}
    */

    // ========================================================
    // VARIANT [v2] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t1_redundant_ops;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;
import java.util.stream.Collectors;

/**
 * 🚀 Variant 2: Parallel Batch Processing
 * Uses thread pool to execute batch saves concurrently for maximum throughput.
 */
public class T1_RedundantOpsExample_V2 {

    private static final int BATCH_SIZE = 100;
    private static final int THREAD_COUNT = 4;
    private final ExecutorService executor = Executors.newFixedThreadPool(THREAD_COUNT);

    // ✅ Optimal: Parallel batch processing
    public void processOptimal(List<String> items) {
        if (items == null || items.isEmpty()) return;

        // Partition items into batches
        List<List<String>> batches = new ArrayList<>();
        for (int i = 0; i < items.size(); i += BATCH_SIZE) {
            int end = Math.min(i + BATCH_SIZE, items.size());
            batches.add(items.subList(i, end));
        }

        // Submit all batches for parallel execution
        List<CompletableFuture<Void>> futures = batches.stream()
            .map(batch -> CompletableFuture.runAsync(() -> saveBatchToDatabase(batch), executor))
            .collect(Collectors.toList());

        // Wait for all batches to complete
        CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();
    }

    private void saveBatchToDatabase(List<String> items) {
        // Simulated batch save with JDBC batching
    }

    public void shutdown() {
        executor.shutdown();
    }
}
    */

    // ========================================================
    // VARIANT [v3] [CANDIDATE VARIANT]
    // ========================================================
    /*
package examples.t1_redundant_ops;

import java.util.ArrayList;
import java.util.List;
import java.util.Spliterator;
import java.util.Spliterators;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

/**
 * 🚀 Variant 3: Stream-based Reactive Batching
 * Uses Java Stream API with custom collector for declarative batch processing.
 */
public class T1_RedundantOpsExample_V3 {

    private static final int BATCH_SIZE = 100;

    // ✅ Optimal: Stream-based batch processing with backpressure
    public void processOptimal(List<String> items) {
        if (items == null || items.isEmpty()) return;

        // Convert to stream and batch using custom collector
        batchStream(items.stream(), BATCH_SIZE)
            .forEach(this::saveBatchToDatabase);
    }

    private Stream<List<String>> batchStream(Stream<String> stream, int batchSize) {
        return StreamSupport.stream(
            new Spliterators.AbstractSpliterator<List<String>>(
                Long.MAX_VALUE, Spliterator.ORDERED | Spliterator.NONNULL
            ) {
                private final java.util.Iterator<String> iterator = stream.iterator();

                @Override
                public boolean tryAdvance(java.util.function.Consumer<? super List<String>> action) {
                    List<String> batch = new ArrayList<>(batchSize);
                    while (iterator.hasNext() && batch.size() < batchSize) {
                        batch.add(iterator.next());
                    }
                    if (batch.isEmpty()) {
                        return false;
                    }
                    action.accept(batch);
                    return true;
                }
            }, false
        );
    }

    private void saveBatchToDatabase(List<String> items) {
        // Simulated batch save with JDBC batching
    }
}
    */

}
