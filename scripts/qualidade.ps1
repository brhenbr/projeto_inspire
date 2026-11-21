# Atalho para o PowerShell: executa o portão de qualidade via Git Bash.
# Uso (na raiz do repositório):  .\scripts\qualidade.ps1
bash "$PSScriptRoot/qualidade.sh"
exit $LASTEXITCODE
