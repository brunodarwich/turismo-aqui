param(
    [Parameter(Mandatory)][string] $Roteiro,
    [Parameter(Mandatory)][string] $Pasta
)

$ErrorActionPreference = 'Stop'
$cenas = (Get-Content -LiteralPath $Roteiro -Raw -Encoding utf8 | ConvertFrom-Json).video
$narrador = New-Object -ComObject SAPI.SpVoice
try {
    $vozes = $narrador.GetVoices('Language=416')
    if ($vozes.Count -gt 0) { $voz = $vozes.Item(0) }
} catch [System.Runtime.InteropServices.COMException] {
    # Há instalações que expõem o token da Maria sem permitir enumerar a categoria.
    $voz = $null
}
if (-not $voz) {
    $tokenId = 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_PT-BR_MARIA_11.0'
    if (-not (Test-Path -LiteralPath ('Registry::' + $tokenId))) {
        throw 'Nenhuma voz SAPI em português do Brasil foi localizada.'
    }
    $voz = New-Object -ComObject SAPI.SpObjectToken
    $voz.SetId($tokenId)
}

$narrador.Voice = $voz
$narrador.Rate = 1
for ($indice = 0; $indice -lt $cenas.Count; $indice++) {
    $saida = New-Object -ComObject SAPI.SpFileStream
    try {
        $arquivo = Join-Path $Pasta ('cena-{0}.wav' -f $indice)
        $saida.Open($arquivo, 3, $false)
        $narrador.AudioOutputStream = $saida
        $null = $narrador.Speak($cenas[$indice].fala, 0)
    } finally {
        $saida.Close()
    }
}
Write-Output ($narrador.Voice.GetDescription())
