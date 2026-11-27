from src.generators.base_generator import BaseGenerator


class PostgreSQLGenerator(BaseGenerator):
    """Render PostgreSQL SQL from the common IR."""

    def generate(self, node) -> str:
        raise NotImplementedError("PostgreSQL SQL rendering is not implemented yet.")
