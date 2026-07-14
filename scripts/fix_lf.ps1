$path = "c:\projects\cdc\vpn\entrypoint.sh"
$content = [System.IO.File]::ReadAllText($path)
$content = $content.Replace("`r`n", "`n")
[System.IO.File]::WriteAllText($path, $content)
Write-Output "Successfully converted CRLF to LF in $path"

$path2 = "c:\projects\cdc\dashboard\entrypoint.sh"
$content2 = [System.IO.File]::ReadAllText($path2)
$content2 = $content2.Replace("`r`n", "`n")
[System.IO.File]::WriteAllText($path2, $content2)
Write-Output "Successfully converted CRLF to LF in $path2"
