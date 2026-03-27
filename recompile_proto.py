import argparse
from pathlib import Path
import subprocess
import sys

PROTO_DIR = Path("utils/pb")


def get_services():
    return [
        file.stem
        for file in PROTO_DIR.iterdir()
        if file.suffix == ".proto"
    ]


def ensure_output_directory():
    output_dir = PROTO_DIR / "services"
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    elif not output_dir.is_dir():
        raise RuntimeError(f"{output_dir} is not a directory.")
    

def append_service_pathes(service_file):
    with open(service_file, "r") as f:
        lines = f.readlines()

    lines = [
        'import sys\n',
        'import os\n',
        'FILE = __file__ if "__file__" in globals() else os.getenv("PYTHONFILE", "")\n',
        'utils_path = os.path.abspath(os.path.join(FILE, "../"))\n',
        'sys.path.insert(0, utils_path)\n',
    ] + lines

    with open(service_file, "w") as f:
        for line in lines:
            f.write(line)


def proto_command_local(service: str):
    ensure_output_directory()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            "-I.",
            "--python_out=./services",
            "--pyi_out=./services",
            "--grpc_python_out=./services",
            f"{service}.proto",
        ],
        check=True,
        cwd=PROTO_DIR,
    )
    append_service_pathes(PROTO_DIR / "services" / f"{service}_pb2.py")


def proto_command_docker(service: str):
    ensure_output_directory()
    subprocess.run(
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "--no-deps",
            "orchestrator",
            "python",
            "-m",
            "grpc_tools.protoc",
            "-I./utils/pb",
            f"--python_out=./utils/pb/{service}",
            f"--pyi_out=./utils/pb/{service}",
            f"--grpc_python_out=./utils/pb/{service}",
            f"./utils/pb/{service}.proto",
        ],
        check=True,
    )


def run_proto(services, mode: str):
    for service in services:
        if mode == "docker":
            proto_command_docker(service)
        else:
            proto_command_local(service)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recompile gRPC protobuf stubs for local services."
    )
    parser.add_argument(
        "--mode",
        choices=["docker", "local"],
        default="local",
        help=(
            "Compile inside Docker by default to match container protobuf runtime "
            "(prevents gencode/runtime version mismatches)."
        ),
    )
    args = parser.parse_args()

    services = get_services()
    run_proto(services, args.mode)
