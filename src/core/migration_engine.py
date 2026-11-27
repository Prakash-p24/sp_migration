"""Public application service for stored-procedure migration."""


class MigrationNotImplementedError(RuntimeError):
    """Raised when the requested dialect pair has no complete pipeline yet."""


class MigrationEngine:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline

    def migrate_sql(self, sql: str, source_dialect: str, target_dialect: str = "postgres"):
        if self.pipeline is None:
            raise MigrationNotImplementedError("Migration pipeline has not been configured.")
        return self.pipeline.run(sql, source_dialect, target_dialect)
