"""SQLite guards for dynamic result values and definitions already in use."""

from sqlalchemy import Engine


def install_metric_constraints(engine: Engine) -> None:
    with engine.begin() as connection:
        for operation in ("INSERT", "UPDATE"):
            connection.exec_driver_sql(f"""
                CREATE TRIGGER IF NOT EXISTS validate_custom_metrics_{operation.lower()}
                BEFORE {operation} ON experiment_results
                BEGIN
                    SELECT RAISE(ABORT, 'custom metric must be finite numeric')
                    WHERE EXISTS (SELECT 1 FROM json_each(NEW.custom_metrics)
                                  WHERE type NOT IN ('integer', 'real')
                                  OR abs(value) > 1.7976931348623157e308);
                    SELECT RAISE(ABORT, 'unknown custom metric or invalid range')
                    WHERE EXISTS (
                        SELECT 1 FROM json_each(NEW.custom_metrics) AS v
                        LEFT JOIN project_metrics AS m ON m.key = v.key AND m.project_id = (
                            SELECT b.project_id FROM experiments e JOIN experiment_batches b
                            ON b.id = e.batch_id WHERE e.id = NEW.experiment_id)
                        WHERE m.id IS NULL OR (m.lower_bound IS NOT NULL AND v.value < m.lower_bound)
                        OR (m.upper_bound IS NOT NULL AND v.value > m.upper_bound));
                END
            """)
        used = """EXISTS (
            SELECT 1 FROM experiment_results r JOIN experiments e ON e.id = r.experiment_id
            JOIN experiment_batches b ON b.id = e.batch_id
            WHERE b.project_id = OLD.project_id
            AND json_extract(r.custom_metrics, '$.' || OLD.key) IS NOT NULL)"""
        connection.exec_driver_sql(f"""
            CREATE TRIGGER IF NOT EXISTS restrict_used_metric_delete
            BEFORE DELETE ON project_metrics WHEN {used}
            BEGIN SELECT RAISE(ABORT, 'metric is in use'); END
        """)
        connection.exec_driver_sql(f"""
            CREATE TRIGGER IF NOT EXISTS restrict_used_metric_update
            BEFORE UPDATE ON project_metrics WHEN {used} AND (
                NEW.key IS NOT OLD.key OR NEW.project_id IS NOT OLD.project_id
                OR NEW.unit IS NOT OLD.unit OR NEW.direction IS NOT OLD.direction
                OR NEW.lower_bound IS NOT OLD.lower_bound OR NEW.upper_bound IS NOT OLD.upper_bound)
            BEGIN SELECT RAISE(ABORT, 'metric is in use'); END
        """)
