import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DIR_TO_WATCH = '/app'

class OnAnyModifiedFileHandler(FileSystemEventHandler):
    def __init__(self, script):
        self.script = script
        self.process = None
        self.pending_files = {}
        self.idle_time = 0.5 
        self.start_script() # Start it initially here

    def start_script(self):
        # Start the subprocess
        self.process = subprocess.Popen([sys.executable, self.script])

    def on_modified(self, event):
        if event.is_directory or '__pycache__' in event.src_path:
            return 
        self.pending_files[event.src_path] = time.time()

    def check_for_closed_files(self):
        current_time = time.time()
        if not self.pending_files:
            return

        # Check if the most recent change has "settled"
        latest_change = max(self.pending_files.values())
        if current_time - latest_change > self.idle_time:
            print(f"Changes detected. Restarting: {self.script}")
            self.pending_files.clear() # Clear all pending at once
            self.restart_script()

    def restart_script(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5) # Wait for it to actually die
            except subprocess.TimeoutExpired:
                self.process.kill() # Force kill if it's stubborn
        
        self.start_script()

def main(script):
    event_handler = OnAnyModifiedFileHandler(script)
    observer = Observer()
    observer.schedule(event_handler, DIR_TO_WATCH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(0.5)
            event_handler.check_for_closed_files()
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()

if __name__ == '__main__':
    main(sys.argv[1])