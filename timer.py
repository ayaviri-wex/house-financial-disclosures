import time

class Timer:
    def __init__(self, block_name: str):
        self.block_name = block_name
        self.start_time = 0

    def __enter__(self):
        self.start_time = time.time()
        print(f"Starting {self.block_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_time = time.time() - self.start_time
        print(f"Finished {self.block_name} in {elapsed_time:.4f} seconds")

        # Returning False (the default behavior) will re-raise any exception
        # that occurred within the 'with' block, which is usually desired.
        return False
