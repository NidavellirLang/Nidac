from tester import Tester

test = Tester("IF TEST")
test.run_pass_test("if_tests_pass")
test.run_fail_test("if_tests_error")
test.print_status()
