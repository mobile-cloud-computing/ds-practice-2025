import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional


# ----- Configuration -----
@dataclass
class GrpcConfig:
    """Configuration for microservice paths and their names."""

    names: List[str] = field(
        default_factory=lambda: [
            "suggestions",
            "transaction_verification",
            "fraud_detection",
        ]
    )
    base_path: str = ""
    max_depth: int = 10  # Maximum depth to search for paths

    def init_paths(self, file_path: str) -> None:
        """Initialize the base path from the file path."""
        self.base_path = file_path

    def find_directory(
        self, target_dir: str, max_depth: Optional[int] = None
    ) -> Optional[str]:
        """
        Recursively search for a target directory by traversing up the directory tree.

        Args:
            target_dir: The directory to find (e.g., "utils/pb")
            max_depth: Maximum number of parent directories to check

        Returns:
            The absolute path to the directory if found, None otherwise
        """
        max_depth = self.max_depth

        current_path = os.path.dirname(os.path.abspath(self.base_path))

        for _ in range(max_depth):
            # current level
            candidate_path = os.path.join(current_path, target_dir)
            if os.path.isdir(candidate_path):
                return candidate_path

            # one dir up
            current_path = os.path.dirname(current_path)

            # stop if not found in root
            if current_path == os.path.dirname(current_path):
                break

        print(
            f"Warning: Could not find directory '{target_dir}' in any parent directory"
        )
        return None

    def get_grpc_path(self, microservice: str) -> str:
        """Get the path for a specific microservice's gRPC definition."""
        # Try to find the utils/pb directory
        pb_dir = self.find_directory("utils/pb")

        if pb_dir:
            # Use the found utils/pb directory and append the microservice name
            return os.path.join(pb_dir, microservice)
        else:
            # fllaback to the original hardcoded path
            return os.path.abspath(
                os.path.join(
                    os.path.dirname(self.base_path),
                    f"../../../../utils/pb/{microservice}",
                )
            )

    def get_models_path(self) -> str:
        """Get the path for models."""
        # Try to find the utils/models directory
        models_dir = self.find_directory("utils/models")

        if models_dir:
            return models_dir
        else:
            # Fallback to the original hardcoded path
            return os.path.abspath(
                os.path.join(
                    os.path.dirname(self.base_path), "../../../../utils/models"
                )
            )

    def setup_paths(self) -> None:
        """Set up all paths in sys.path."""
        for microservice in self.names:
            path = self.get_grpc_path(microservice)
            if path not in sys.path:
                print(f"Adding {path} to sys.path")
                sys.path.insert(0, path)

        models_path = self.get_models_path()
        if models_path and models_path not in sys.path:
            print(f"Adding {models_path} to sys.path")
            sys.path.insert(0, models_path)
