import time


class ExecutionTimer:
    def __init__(self):
        self.start_time = time.perf_counter()
        self.temp_time = None

        self.current_watch = None

        self.timers = {}
        self.max_str_len = 0

    def name_update(self, name):
        self.max_str_len = max(self.max_str_len, len(name) + 1)
        self.current_watch = name

    def start(self, name):
        if self.current_watch is not None:
            self.stop()

        self.name_update(name)
        self.temp_time = time.perf_counter()

    def stop(self):
        if self.current_watch is None:
            raise Exception("Not watching a timer")

        self.timers[self.current_watch] = time.perf_counter() - self.temp_time

        self.current_watch = None

    def calc_air(self, name):
        name_len = len(name)
        air_len = self.max_str_len - name_len
        return " " * air_len

    def print(self):
        if self.current_watch is not None:
            self.stop()

        print("\n")

        for name, times in self.timers.items():
            air = self.calc_air(name)
            print(f"{name}{air}: {times:.3f} seconds")

        end_time = time.perf_counter()

        print(f"\nTotal: {end_time-self.start_time:.3f} seconds\n")
