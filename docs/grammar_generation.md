# ANTLR Grammar Generation

ANTLR generator and Python runtime should remain version-aligned. This project currently pins `antlr4-python3-runtime` to `4.13.2` and includes `src/antlr-4.13.2-complete.jar`.

From the repository root in PowerShell:

```powershell
.\scripts\generate_mssql_parser.ps1
```

Edit `.g4` files, not generated `.py`, `.tokens` or `.interp` files. Generate the lexer first, then the parser using the lexer token vocabulary via `-lib`. Generated `.py` modules are required at runtime; `.g4`, `.tokens`, `.interp` and the JAR are normally build/development assets and can be excluded from a production runtime image after a clean-package test.
