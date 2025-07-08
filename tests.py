from functions.run_python import run_python_file

normal_run_1 = run_python_file("calculator", "main.py")
normal_run_2 = run_python_file("calculator", "tests.py")
error_run_1 = run_python_file("calculator", "../main.py")
error_run_2 = run_python_file("calculator", "nonexistent.py")

print(normal_run_1)
print(normal_run_2)
print(error_run_1)
print(error_run_2)