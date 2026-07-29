package ru.hackathon.profiling.sensorhub.harness;

import java.util.concurrent.atomic.AtomicLong;

public class SqlCounter {
    private static final ThreadLocal<AtomicLong> COUNT = ThreadLocal.withInitial(AtomicLong::new);
    private static final ThreadLocal<Long> START_TIME = ThreadLocal.withInitial(System::currentTimeMillis);

    public static void reset() {
        COUNT.get().set(0);
        START_TIME.set(System.currentTimeMillis());
    }

    public static void increment() {
        COUNT.get().incrementAndGet();
    }

    public static long getCount() {
        return COUNT.get().get();
    }

    public static long getElapsedMs() {
        return System.currentTimeMillis() - START_TIME.get();
    }

    public static void clear() {
        COUNT.remove();
        START_TIME.remove();
    }
}
