# Manuel PyQt6 kurulumu - wheel'leri indirip yerel kurar (SSL atlanir)
# PowerShell'de: .\install_manual.ps1

$ErrorActionPreference = "Stop"
$wheelsDir = Join-Path $PSScriptRoot "wheels"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Host "Python bulunamadi. PATH'e ekleyin." -ForegroundColor Red; exit 1 }

New-Item -ItemType Directory -Force -Path $wheelsDir | Out-Null

# PyQt6 6.10.1 - Windows 64-bit (cp39-abi3 = Python 3.9+)
$urls = @(
    "https://files.pythonhosted.org/packages/53/5c/648c515d57bc82909d0597befb03bbc2f7a570f323dba3ad38629669efcb/pyqt6_qt6-6.10.1-py3-none-win_amd64.whl",
    "https://files.pythonhosted.org/packages/7e/87/465ea8df9936190c133671e07370e17a0fa8fa55308c8742e544cdf3556c/pyqt6-6.10.1-cp39-abi3-win_amd64.whl"
)

Write-Host "Wheel dosyalari indiriliyor (~100 MB)..." -ForegroundColor Cyan
foreach ($url in $urls) {
    $name = Split-Path $url -Leaf
    $path = Join-Path $wheelsDir $name
    if (Test-Path $path) {
        Write-Host "  Zaten var: $name" -ForegroundColor Gray
    } else {
        Write-Host "  Indiriliyor: $name"
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $url -OutFile $path -UseBasicParsing
        } catch {
            Write-Host "  HATA: $_" -ForegroundColor Red
            Write-Host "  Bu dosyayi tarayicidan indirip $wheelsDir icinde $name olarak kaydedin." -ForegroundColor Yellow
            exit 1
        }
    }
}

Write-Host "`nPyQt6-sip, PyOpenGL, numpy kuruluyor (kucuk paketler - pip ile)..." -ForegroundColor Cyan
& $py -m pip install PyQt6-sip PyOpenGL numpy --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyQt6-sip kurulumu basarisiz. Deniyorum: pip install PyQt6-sip" -ForegroundColor Yellow
    & $py -m pip install PyQt6-sip
}

Write-Host "`nYerel wheel'lerden PyQt6 kuruluyor..." -ForegroundColor Cyan
& $py -m pip install --no-index --find-links $wheelsDir pyqt6_qt6 pyqt6

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nKurulum tamamlandi. Calistirmak icin: python main.py" -ForegroundColor Green
} else {
    Write-Host "`nKurulum hatasi. INSTALL_WINDOWS.md dosyasina bakin." -ForegroundColor Red
    exit 1
}
