# Testing Strategy

1. Unit-test lexer/parser behavior and parser error reporting.
2. Unit-test parse-tree-to-IR visitors.
3. Unit-test each converter using small IR fixtures.
4. Test deterministic PostgreSQL generation.
5. Maintain golden-file regression cases: source procedure and expected target SQL.
6. Run integration tests against disposable source/target database instances where possible.

Successful parsing does not prove semantic equivalence. Validate generated SQL and test behavior separately.
