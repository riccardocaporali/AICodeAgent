# calculator.py

class Calculator:
    def __init__(self):
        self.operators = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b,
        }
        self.precedence = {
            "+": 2,
            "-": 2,
            "*": 3,
            "/": 3,
        }

    def evaluate(self, expression):
        if not expression or expression.isspace():
            return None
        tokens = expression.strip().split()
        return self._evaluate_shunting_yard(tokens)

    def _evaluate_shunting_yard(self, tokens):
        output_queue = []
        operator_stack = []

        for token in tokens:
            if token in self.operators:
                while (operator_stack and operator_stack[-1] in self.operators and
                       self.precedence[token] <= self.precedence[operator_stack[-1]]):
                    output_queue.append(operator_stack.pop())
                operator_stack.append(token)
            elif self._is_number(token):
                output_queue.append(token)
            elif token == "(":
                operator_stack.append(token)
            elif token == ")":
                while operator_stack and operator_stack[-1] != "(":
                    output_queue.append(operator_stack.pop())
                operator_stack.pop()  # Discard the "("
            else:
                raise ValueError(f"Invalid token: {token}")

        while operator_stack:
            if operator_stack[-1] == "(" or operator_stack[-1] == ")":
                raise ValueError("Mismatched parentheses")
            output_queue.append(operator_stack.pop())

        return self._evaluate_postfix(output_queue)

    def _evaluate_postfix(self, tokens):
        stack = []
        for token in tokens:
            if self._is_number(token):
                stack.append(float(token))
            elif token in self.operators:
                if len(stack) < 2:
                    raise ValueError("Not enough operands for operator")
                operand2 = stack.pop()
                operand1 = stack.pop()
                result = self.operators[token](operand1, operand2)
                stack.append(result)
            else:
                raise ValueError(f"Invalid token: {token}")

        if len(stack) != 1:
            raise ValueError("Invalid expression")
        return stack[0]

    def _is_number(self, token):
        try:
            float(token)
            return True
        except ValueError:
            return False
