# Conversion Rules

Implement conversion against the common IR rather than performing broad text replacement on entire procedure bodies.

For every conversion rule, record:
- source dialect and construct;
- target representation;
- semantic differences and required caveats;
- unsupported cases;
- input SQL fixture and expected PostgreSQL output.

Do not silently discard unsupported statements. Emit a diagnostic with source object and line/column when possible.
