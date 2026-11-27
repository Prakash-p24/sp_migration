"""Dialect-neutral semantic decisions applied after syntax parsing."""

from src.ir.enums import SelectIntent


class SelectIntentAnalyzer:
    """Infer what a SELECT does from its surrounding T-SQL context."""

    @staticmethod
    def analyze(*, has_variable_assignment: bool, has_into_table: bool) -> SelectIntent:
        if has_variable_assignment:
            return SelectIntent.VARIABLE_ASSIGNMENT
        if has_into_table:
            return SelectIntent.INTO_TABLE
        # A standalone SELECT is a row-producing query in the source language.
        return SelectIntent.RESULT_SET
