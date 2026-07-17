# ============================================================
# merge_music.ps1
# Merge 5 background music segments (Awe, Tension, Grief, Hope,
# Reflection) into one seamless track using crossfade.
#
# NOTE: Google Flash/Lyria exports files that contain 30 seconds
# of real music followed by silence padding out to whatever
# timeline length was set in the tool (e.g. a "30s" generation
# can come out as a 174s file: 30s of audio + ~144s of silence).
# This script trims every input file down to exactly the first
# 30 seconds BEFORE crossfading, so the silence padding never
# ends up baked into the merged track.
#
# REQUIRES: ffmpeg installed and available in PATH
#           (check with: ffmpeg -version)
#
# HOW TO USE:
#   1. Put your 5 audio files in the SAME folder as this script.
#      Rename them to match the names below, OR edit the 5
#      variables ($File1 .. $File5) to match your actual filenames.
#   2. Run it. If you get an "execution policy" error, run this
#      ONCE first (no admin needed):
#        Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#      Or run without changing policy:
#        powershell -ExecutionPolicy Bypass -File .\merge_music.ps1
#   3. Output: final_theme_music.mp3 in the same folder.
# ============================================================

$ErrorActionPreference = "Stop"

# ---- CONFIG: rename these to match your actual files ----
$File1 = "1_awe.mp3"
$File2 = "2_tension.mp3"
$File3 = "3_grief.mp3"
$File4 = "4_hope.mp3"
$File5 = "5_reflection.mp3"

$Output = "final_theme_music.mp3"

$CrossfadeSec = 0.75

# How many seconds of REAL music each source file actually has
# before the silence padding starts. Google Flash/Lyria generates
# 30s of audio, so this trims every file down to that length
# before crossfading. Change this if your tool's real clip length
# is different.
$RealClipSec = 30

$TmpDir = "_tmp_clean"

# ---- CHECK FFMPEG ----
$ffmpegCheck = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpegCheck) {
    Write-Host "ERROR: ffmpeg not found in PATH." -ForegroundColor Red
    Write-Host "Install it first:" -ForegroundColor Yellow
    Write-Host "  Option 1: winget install ffmpeg"
    Write-Host "  Option 2: download from https://www.gyan.dev/ffmpeg/builds/"
    Write-Host "            unzip it, then add the 'bin' folder to your PATH."
    exit 1
}

# ---- CHECK FILES EXIST ----
$files = @($File1, $File2, $File3, $File4, $File5)
foreach ($f in $files) {
    if (-not (Test-Path $f)) {
        Write-Host "ERROR: File not found: $f" -ForegroundColor Red
        Write-Host "Put your 5 music files in this folder with matching names,"
        Write-Host "or edit File1..File5 at the top of this script."
        exit 1
    }
}

Write-Host "Found all 5 files. Starting merge..." -ForegroundColor Green

# ---- STEP 1: trim each file to the real clip length, then fade
#      in/out to avoid clicks on crossfade, normalize sample
#      rate / codec ----
if (Test-Path $TmpDir) { Remove-Item $TmpDir -Recurse -Force }
New-Item -ItemType Directory -Path $TmpDir | Out-Null

# Fade-out starts slightly before the trim point so it never
# reaches into silence (e.g. for a 30s clip, fade starts at 29.4s).
$fadeOutStart = $RealClipSec - 0.6

$i = 1
foreach ($f in $files) {
    Write-Host "  Processing: $f (trimming to first $RealClipSec s)"
    $outClean = Join-Path $TmpDir "clean_$i.wav"
    & ffmpeg -y -i $f `
        -t $RealClipSec `
        -af "afade=t=in:st=0:d=0.3,afade=t=out:st=$fadeOutStart`:d=0.6" `
        -ar 44100 -ac 2 -c:a pcm_s16le `
        $outClean -loglevel error
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: ffmpeg failed while processing $f" -ForegroundColor Red
        exit 1
    }
    $i++
}

# ---- STEP 2: crossfade merge in sequence (1 -> 2 -> 3 -> 4 -> 5) ----
Write-Host "  Crossfading segments together..."

$c1 = Join-Path $TmpDir "clean_1.wav"
$c2 = Join-Path $TmpDir "clean_2.wav"
$c3 = Join-Path $TmpDir "clean_3.wav"
$c4 = Join-Path $TmpDir "clean_4.wav"
$c5 = Join-Path $TmpDir "clean_5.wav"

# Build the filter_complex string and write it to a temp script file.
# This avoids PowerShell mangling ':' and ';' characters when passed
# directly as a command-line argument to ffmpeg.
$filterComplex = "[0][1]acrossfade=d=$CrossfadeSec" + ":c1=tri:c2=tri[a01];" +
                 "[a01][2]acrossfade=d=$CrossfadeSec" + ":c1=tri:c2=tri[a012];" +
                 "[a012][3]acrossfade=d=$CrossfadeSec" + ":c1=tri:c2=tri[a0123];" +
                 "[a0123][4]acrossfade=d=$CrossfadeSec" + ":c1=tri:c2=tri[out]"

$filterFile = Join-Path $TmpDir "filter.txt"
[System.IO.File]::WriteAllText($filterFile, $filterComplex, (New-Object System.Text.UTF8Encoding($false)))

& ffmpeg -y `
    -i $c1 -i $c2 -i $c3 -i $c4 -i $c5 `
    -filter_complex_script $filterFile `
    -map "[out]" -c:a libmp3lame -q:a 2 `
    $Output -loglevel error

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ffmpeg failed during crossfade merge." -ForegroundColor Red
    Write-Host "Filter used (for debugging):"
    Write-Host $filterComplex
    exit 1
}

Remove-Item $TmpDir -Recurse -Force

Write-Host ""
Write-Host "DONE!" -ForegroundColor Green
Write-Host "Output file: $Output"

$durationOutput = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $Output
$durationSec = [double]$durationOutput
$durationMin = [math]::Round($durationSec / 60, 1)
Write-Host "Total duration: $([math]::Round($durationSec,1)) seconds (~$durationMin minutes)"

$expectedSec = ($RealClipSec * 5) - ($CrossfadeSec * 4)
Write-Host "Expected duration: ~$expectedSec seconds"

Write-Host ""
Write-Host "TIP: if your video is longer, loop the whole file with:" -ForegroundColor Yellow
Write-Host "  ffmpeg -stream_loop -1 -i $Output -t <VIDEO_LENGTH_IN_SECONDS> -c copy looped_output.mp3"
