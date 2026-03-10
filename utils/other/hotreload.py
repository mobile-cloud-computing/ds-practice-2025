import sys
import time
import subprocess
import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging for the hotreloader
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [HOTRELOAD] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

DIR_TO_WATCH = '/app'

class OnAnyModifiedFileHandler(FileSystemEventHandler):
    def __init__(self, script):
        self.script = script
        self.process = None
        self.pending_files = {}
        self.idle_time = 0.5 
        self.start_script()

    def start_script(self):
        # Start the subprocess and inherit stdout/stderr
        self.process = subprocess.Popen(
            [sys.executable, self.script],
            stdout=None,
            stderr=None
        )

    def on_modified(self, event):
        # Ignore directories and pycache
        if event.is_directory or '__pycache__' in event.src_path:
            return 
        self.pending_files[event.src_path] = time.time()

    def check_for_closed_files(self):
        if not self.pending_files:
            return

        current_time = time.time()
        # Check if the most recent change has "settled" (Debounce)
        latest_change = max(self.pending_files.values())
        
        if current_time - latest_change > self.idle_time:
            logging.info(f"File changes detected. Restarting: {self.script}")
            self.pending_files.clear()
            self.restart_script()

    def restart_script(self):
        if self.process:
            # Send termination signal
            self.process.terminate()
            try:
                # Wait up to 5 seconds for clean exit
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.warning(f"Process {self.script} did not terminate. Killing...")
                self.process.kill()
                self.process.wait()
        
        self.start_script()

def main(script):
    logging.info(f"Watching directory: {DIR_TO_WATCH} for changes in {script}")
    event_handler = OnAnyModifiedFileHandler(script)
    observer = Observer()
    observer.schedule(event_handler, DIR_TO_WATCH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(0.5)
            event_handler.check_for_closed_files()
    except KeyboardInterrupt:
        logging.info("Hotreloader shutting down...")
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("Usage: python hotreload.py <script>")
        sys.exit(1)
    main(sys.argv[1])