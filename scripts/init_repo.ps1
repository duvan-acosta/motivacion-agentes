# Script de inicialización local (git + commits iniciales)
# Ejecutar en PowerShell: .\scripts\init_repo.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path .git)) {
    git init -b main
    Write-Host "Repositorio git inicializado."
}

git add .gitignore .env.example requirements.txt Dockerfile docker-compose.yml README.md
git add config/ rag/ utils/ scheduler/ scripts/ __init__.py
git status --short

$msg1 = @"
Scaffold inicial: config, RAG knowledge, Docker y utilidades.

Incluye corpus en español, ChromaDB store, docker-compose con FFmpeg
y variables de entorno documentadas.
"@

git commit -m $msg1 2>$null
if ($LASTEXITCODE -ne 0) {
    git commit -m "Scaffold inicial: config, RAG knowledge, Docker y utilidades"
}

git add agents/ pipelines/ publishing/ graph/ cli/
$msg2 = @"
Implementa agentes, pipelines de medios, publicación y CLI.

LangGraph end-to-end, adaptadores Meta/TikTok/YouTube/X,
generación multi-plataforma y comandos generate/publish/status/schedule.
"@

git commit -m $msg2 2>$null
if ($LASTEXITCODE -ne 0) {
    git commit -m "Implementa agentes, pipelines, publicación y CLI"
}

Write-Host "`nCommits creados:"
git log --oneline -2

Write-Host "`nPara GitHub (si gh está autenticado):"
Write-Host "  gh repo create motivacion-agentes --public --source=. --remote=origin --push"
