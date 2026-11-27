$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Jar = Join-Path $Root "src\antlr-4.13.2-complete.jar"
$Grammar = Join-Path $Root "src\grammar\mssql"
$Output = Join-Path $Root "src\generated\mssql"
New-Item -ItemType Directory -Force -Path $Output | Out-Null
Push-Location $Grammar
try {
    java -jar $Jar -Dlanguage=Python3 -visitor -no-listener -o $Output TSqlLexer.g4
    java -jar $Jar -Dlanguage=Python3 -visitor -no-listener -lib $Output -o $Output TSqlParser.g4
}
finally { Pop-Location }


# Install Java
https://adoptium.net/?utm_source=chatgpt.com

# Download ANTLR JAR
https://www.antlr.org/download/antlr-4.13.2-complete.jar?utm_source=chatgpt.com

# Install Dependency
poetry add antlr4-python3-runtime==4.13.2

# Generate Lexer
& "C:\Program Files\Eclipse Adoptium\jdk-25.0.5.10002-hotspot\bin\java.exe" `
    -jar ..\antlr-4.13.2-complete.jar `
    -Dlanguage=Python3 `
    -o ..\generated `
    TSqlLexer.g4

# Generate Parser
& "C:\Program Files\Eclipse Adoptium\jdk-25.0.5.10002-hotspot\bin\java.exe" `
    -jar ..\antlr-4.13.2-complete.jar `
    -Dlanguage=Python3 `
    -visitor `
    -no-listener `
    -lib ..\generated `
    -o ..\generated `
    TSqlParser.g4
