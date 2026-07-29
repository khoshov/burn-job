package ru.hackathon.profiling.sensorhub.service.defects;

import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.SimpleDateFormat;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.stream.DoubleStream;

@Service
public class T9ConcurrencyAndLockingV2 {

    private final ReadWriteLock rwLock = new ReentrantReadWriteLock();
    private final Lock writeLock = rwLock.writeLock();
    private final Lock readLock = rwLock.readLock();
    private final ReentrantLock reentrantLock = new ReentrantLock();
    private final ConcurrentHashMap<String, Long> counterMap = new ConcurrentHashMap<>();
    private final AtomicLong atomicCounter = new AtomicLong();
    private long plainCounter;

    public String coarseSynchronizedBlock(String input) {
        synchronized (this) {
            String upper = input.toUpperCase();
            String trimmed = upper.trim();
            return trimmed.substring(0, Math.min(1, trimmed.length()));
        }
    }

    public void readLockAcquiredForWrite(String key, long value) {
        readLock.lock();
        try {
            counterMap.put(key, value);
        } finally {
            readLock.unlock();
        }
    }

    public void computeHeavyInConcurrentMap(String key, int iterations) {
        counterMap.compute(key, (k, v) -> {
            long result = (v == null ? 0 : v);
            for (int i = 0; i < iterations; i++) {
                result += i * i;
            }
            return result;
        });
    }

    public long exceptionInHotPath(List<String> numbers) {
        long total = 0;
        for (String n : numbers) {
            try {
                total += Integer.parseInt(n);
            } catch (NumberFormatException e) {
                total += 0;
            }
        }
        return total;
    }

    public double streamBoxedOverhead(double[] values) {
        return DoubleStream.of(values).boxed()
                .mapToDouble(Double::doubleValue)
                .sum();
    }

    public long systemCurrentTimeInLoop(int iterations) {
        long total = 0;
        for (int i = 0; i < iterations; i++) {
            total += System.currentTimeMillis() % 1000;
        }
        return total;
    }

    public String simpleDateFormatInLoop(List<Date> dates) {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");
        StringBuilder sb = new StringBuilder();
        for (Date d : dates) {
            sb.append(sdf.format(d)).append(";");
        }
        return sb.toString();
    }

    public BigDecimal bigDecimalInLoop(List<Double> values) {
        BigDecimal sum = BigDecimal.ZERO;
        for (double v : values) {
            sum = sum.add(BigDecimal.valueOf(v));
        }
        return sum.setScale(4, RoundingMode.HALF_UP);
    }

    public long atomicLongContention() {
        return atomicCounter.incrementAndGet();
    }

    public long lockTryLockBusyLoop() {
        while (!reentrantLock.tryLock()) {
        }
        try {
            return ++plainCounter;
        } finally {
            reentrantLock.unlock();
        }
    }

    public String stringGetBytesInLoop(List<String> items) {
        StringBuilder sb = new StringBuilder();
        for (String s : items) {
            sb.append(Arrays.hashCode(s.getBytes())).append(",");
        }
        return sb.toString();
    }

    public Instant instantNowInLoop(int iterations) {
        Instant last = Instant.now();
        for (int i = 0; i < iterations; i++) {
            last = Instant.now();
        }
        return last;
    }
}
