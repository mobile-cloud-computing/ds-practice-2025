import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


"""
This script is designed to run a Python script and watch for file changes in a directory.
When a file is modified in the directory, it restarts the script.

Usage:

python hotreload.py <script>
"""

DIR_TO_WATCH = "/app"


class OnAnyModifiedFileHandler(FileSystemEventHandler):
    def __init__(self, script, process):
        self.script = script
        self.process = process
        self.pending_files = {}
        self.idle_time = 0.5  # Time in seconds to consider a file as "closed"

    def on_modified(self, event):
        if (
            event.is_directory
            or ".log" in event.src_path
            or "__pycache__" in event.src_path
        ):
            return  # Ignore directories and __pycache__

        # Track pending files and their last modification time
        self.pending_files[event.src_path] = time.time()

    def check_for_closed_files(self):
        current_time = time.time()
        files_to_restart = []

        for file_path, last_mod_time in list(self.pending_files.items()):
            if current_time - last_mod_time > self.idle_time:
                files_to_restart.append(file_path)
                del self.pending_files[file_path]

        if files_to_restart:
            print(
                f"Detected closed files: {files_to_restart}. Restarting: {self.script}"
            )
            sys.stdout.flush()
            self.restart_script()

    def restart_script(self):
        # Terminate and restart the process
        if self.process:
            self.process.terminate()
            self.process.wait()

        self.process = subprocess.Popen([sys.executable, self.script])


def main(script):
    process = subprocess.Popen([sys.executable, script])  # Start the script
    event_handler = OnAnyModifiedFileHandler(script, process)
    observer = Observer()
    observer.schedule(event_handler, DIR_TO_WATCH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
            event_handler.check_for_closed_files()  # Check if files are "closed"
    except KeyboardInterrupt:
        observer.stop()
        process.terminate()
    observer.join()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <script>")
        sys.exit(1)
    main(sys.argv[1])
