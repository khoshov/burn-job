package ru.hackathon.profiling.sensorhub.harness;

import org.hibernate.resource.jdbc.spi.StatementInspector;

public class SqlCountInspector implements StatementInspector {

    @Override
    public String inspect(String sql) {
        SqlCounter.increment();
        return sql;
    }
}
