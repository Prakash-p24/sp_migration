# Migration Engine Architecture

The intended flow is:

`Source SQL -> ANTLR Lexer/Parser -> Parse Tree -> Visitor -> Common IR -> Dialect Converter -> PostgreSQL Generator -> Validators -> Output`

- `grammar/`: editable ANTLR grammar source.
- `generated/`: generated ANTLR Python modules; never hand-edit.
- `parsers/`: application adapters around generated parsers.
- `visitors/`: parse-tree traversal and IR construction.
- `ir/`: database-neutral intermediate representation.
- `converters/`: source-dialect IR to target-dialect IR transformations.
- `mappings/`: explicit data type, function, operator and keyword mappings.
- `generators/`: render target SQL from IR.
- `validators/`: syntax, compatibility and generated-output checks.
- `core/`: orchestration only; no dialect-specific grammar logic.

The current working grammar in this repository is MSSQL/T-SQL. MySQL grammar and conversion are placeholders, not implemented features. PostgreSQL is the initial target; a PostgreSQL source parser is optional unless source parsing or output validation requires it.
