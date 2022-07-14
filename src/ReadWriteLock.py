import threading


# implements the Read_Write locks for synchronization
class ReadWriteLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.read_write_lock = threading.Lock()  # To synchronize lock acquiring
        self.readers_count = 0  # Number of readers initially

    def acquire_read_lock(self):
        with self.read_write_lock:
            self.readers_count += 1
            if self.readers_count == 1:
                self.lock.acquire()

    def acquire_write_lock(self):
        self.lock.acquire()

    def release_read_lock(self):
        with self.read_write_lock:
            self.readers_count -= 1
            if self.readers_count == 0:
                self.lock.release()

    def release_write_lock(self):
        self.lock.release()
