@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_migrate_diff.txt
echo ==== WHICH 8 FILES? %DATE% %TIME% ==== > "%OUT%"
echo  Do not accept "8 files short" — NAME them. A diff you cannot name is a diff you cannot dismiss. >> "%OUT%"
echo. >> "%OUT%"
powershell -NoProfile -Command ^
 "$s=Get-ChildItem 'V:\Research4' -Recurse -File -Force -EA SilentlyContinue;" ^
 "$d=Get-ChildItem 'V:\Research4' -Recurse -File -Force -EA SilentlyContinue;" ^
 "$sr=@{}; foreach($f in $s){ $sr[$f.FullName.Substring(13)]=$f }" ^
 "$dr=@{}; foreach($f in $d){ $dr[$f.FullName.Substring(13)]=$f }" ^
 "$missing = $sr.Keys | Where-Object { -not $dr.ContainsKey($_) };" ^
 "'MISSING FROM V:\Research4  (' + ($missing | Measure-Object).Count + ')';" ^
 "foreach($m in $missing){ $f=$sr[$m]; '  {0,10} B  {1}' -f $f.Length,$m };" ^
 "'';" ^
 "$extra = $dr.Keys | Where-Object { -not $sr.ContainsKey($_) };" ^
 "'EXTRA IN V:\Research4  (' + ($extra | Measure-Object).Count + ')';" ^
 "foreach($e in $extra){ '  {0}' -f $e };" ^
 "'';" ^
 "'SIZE DIFFS on files present in BOTH:';" ^
 "$n=0; foreach($k in $sr.Keys){ if($dr.ContainsKey($k)){ if($sr[$k].Length -ne $dr[$k].Length){ $n++; '  SRC {0,10} vs DST {1,10}   {2}' -f $sr[$k].Length,$dr[$k].Length,$k } } }" ^
 "if($n -eq 0){'  none'}" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
