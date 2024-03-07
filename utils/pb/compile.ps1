$directories = Get-ChildItem -Path . -Directory
$currentDir = Get-Location
foreach ($directory in $directories) {
    cd $directory.FullName
    $path = $directory.FullName
    $files = Get-ChildItem -Path $path -Filter *.proto
    foreach ($file in $files) {
        $fileName = $file.Name
        echo "Compiling $fileName"
        python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. ./$fileName
    }
    cd $currentDir
}
