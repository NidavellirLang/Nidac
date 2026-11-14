import time
from pathlib import Path

from nidac_importer import Nidac
from utils.errors import *
from utils import SysArgs

BASE_DIR = Path(__file__).resolve().parent


class Tester:
    def __init__(self, name, verbose=False):
        SysArgs.no_print = not verbose

        self.name = name
        self.verbose = verbose
        self.start_time = time.perf_counter()
        self.error = False
        self.tested_pass = 0
        self.tested_error = 0

    def read_nida_test_file(self, file_path) -> list[str]:
        file_path = BASE_DIR / file_path

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return [test.strip() for test in content.split("#nida_test") if test.strip()]

    def load_tests(self, file_name):
        return self.read_nida_test_file(f"./codes/{file_name}.nida")

    def run_pass_test(self, file_name):
        test = self.load_tests(file_name)
        self.tested_pass += len(test)
        for c, test in enumerate(test):
            try:
                nida = Nidac(source=test)
                nida.compile()

            except Exception as e:
                print(f"[FAIL] Pass-test #{c} failed unexpectedly:")
                print(f"{type(e).__name__}: {e}")
                print("\nTest source:")
                print(test)
                self.error = True

    def run_fail_test(self, file_name):
        test = self.load_tests(file_name)
        self.tested_error += len(test)
        for c, test in enumerate(test):
            try:
                nida = Nidac(source=test)
                nida.compile()

            except NidavellirError as e:
                if self.verbose:
                    print(f"[PASS] Fail-test #{c}: {type(e).__name__}")
                continue

            except Exception as e:
                print(f"[FAIL] Unexpected exception in fail-test #{c}:")
                print(f"{type(e).__name__}: {e}")
                print("\nTest source:")
                print(test)
                self.error = True

            else:
                print(f"[FAIL] Expected error was NOT caught in fail-test #{c}")
                print("\nTest source:")
                print(test)
                self.error = True

    def print_status(self):
        print("\nTest Suite :", self.name)
        if self.error:
            print(
                f"TEST SUITE FAILED, ({self.tested_pass} pass, {self.tested_error} fail)"
            )
        t2 = time.perf_counter()
        print(f"Time taken: {t2 - self.start_time:.6f} seconds")


# EXAMPLE
# t = Tester('if test')
# t.run_pass_test("if_tests_pass")
# t.run_fail_test("if_tests_error")
# t.print_status()
