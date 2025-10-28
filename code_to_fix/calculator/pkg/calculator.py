# calculator.py

class Calculator:
    def __init__(self):
        self.operators = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b
        }

    def evaluate(self, expression):
        try:
            num1, operator, num2 = expression.split()
            num1 = float(num1)
            num2 = float(num2)
            if operator == "/" and num2 == 0:
                return "Division by zero error!"
            operation = self.operators.get(operator)
            if operation:
                return operation(num1, num2)
            else:
                return "Invalid operator!"
        except ValueError:
            return "Invalid input!"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
