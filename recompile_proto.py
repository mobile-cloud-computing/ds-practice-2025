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


def ensure_output_directory(service: str):
    output_dir = PROTO_DIR / service
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    elif not output_dir.is_dir():
        raise RuntimeError(f"{output_dir} is not a directory.")


def proto_command_local(service: str):
    ensure_output_directory(service)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            "-I.",
            f"--python_out=./{service}",
            f"--pyi_out=./{service}",
            f"--grpc_python_out=./{service}",
            f"{service}.proto",
        ],
        check=True,
        cwd=PROTO_DIR,
    )


def proto_command_docker(service: str):
    ensure_output_directory(service)
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
        default="docker",
        help=(
            "Compile inside Docker by default to match container protobuf runtime "
            "(prevents gencode/runtime version mismatches)."
        ),
    )
    args = parser.parse_args()

    services = get_services()
    run_proto(services, args.mode)
