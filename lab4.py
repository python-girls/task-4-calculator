import math
import re


class Calculator:
    def __init__(self):
        self.previous_result = 0
        self.variables = {
            'pi': math.pi,
            'e': math.e
        }

    def calculate(self, expression):
        if not expression.strip():
            return 0

        # Заменяем специальные символы
        expression = expression.replace('_', str(self.previous_result))
        expression = expression.replace(' ', '')

        try:
            result = self._parse_expression(expression)
            self.previous_result = result
            return result
        except Exception as e:
            return f"Ошибка: {str(e)}"

    def _parse_expression(self, expression):

        while '(' in expression:
            expression = self._process_parentheses(expression)

        #разбиваем на токены
        tokens = self._tokenize(expression)

        return self._evaluate_tokens(tokens)

    #сначала то, что в скобках
    def _process_parentheses(self, expression):

        def replace_match(match):
            inner_expr = match.group(1)
            result = self._parse_expression(inner_expr)
            return str(result)

        #самые внутренние скобки
        pattern = r'\(([^()]+)\)'
        while True:
            new_expression = re.sub(pattern, replace_match, expression)
            if new_expression == expression:
                break
            expression = new_expression

        return expression

    def _tokenize(self, expression):
        pattern = r'([+\-*/^()])|(-?\d*\.?\d+)|(\+?inf\b|-inf\b|nan\b)'
        raw_tokens = [match.group() for match in re.finditer(pattern, expression) if match.group()]

        tokens = []
        i = 0
        while i < len(raw_tokens):
            token = raw_tokens[i]

            # Обработка специальных значений
            if token in ['inf', '+inf', '-inf', 'nan']:
                special_map = {
                    'inf': 'INF',
                    '+inf': 'INF',
                    '-inf': 'NEG_INF',
                    'nan': 'NAN'
                }
                tokens.append(special_map[token])
                i += 1
                continue

            if token in ['+', '-']:
                is_unary = (i == 0 or
                            raw_tokens[i - 1] in '+-*/^(' or
                            self._is_operator(raw_tokens[i - 1]))

                if is_unary and i + 1 < len(raw_tokens):
                    next_token = raw_tokens[i + 1]

                    # Обработка специальных значений
                    if next_token in ['inf', '+inf', '-inf', 'nan']:
                        special_unary_map = {
                            ('+', 'inf'): 'INF',
                            ('+', '+inf'): 'INF',
                            ('+', '-inf'): 'NEG_INF',
                            ('-', 'inf'): 'NEG_INF',
                            ('-', '+inf'): 'NEG_INF',
                            ('-', '-inf'): 'INF',
                            ('+', 'nan'): 'NAN',
                            ('-', 'nan'): 'NAN'
                        }
                        tokens.append(special_unary_map[(token, next_token)])
                        i += 2
                        continue

                    elif self._is_number(next_token):
                        tokens.append(token + next_token)
                        i += 2
                        continue

            tokens.append(token)
            i += 1

        return tokens

    def _is_operator(self, token):
        return token in '+-*/^'

    def _evaluate_tokens(self, tokens):
        if not tokens:
            return 0

        #преобразуем токены в числа и операторы
        values = []
        operators = []

        i = 0
        while i < len(tokens):
            token = tokens[i]

            if self._is_number(token):
                values.append(self._parse_number(token))
                i += 1
            elif token in '+-*/^':
                while (operators and operators[-1] != '(' and
                       (self._get_priority(operators[-1]) > self._get_priority(token) or
                        (self._get_priority(operators[-1]) == self._get_priority(token) and token != '^'))):
                    self._apply_operation(values, operators)
                operators.append(token)
                i += 1
            elif token == '(':
                operators.append(token)
                i += 1
            elif token == ')':
                # Вычисляем все до открывающей скобки
                while operators and operators[-1] != '(':
                    self._apply_operation(values, operators)
                if operators and operators[-1] == '(':
                    operators.pop()  # Убираем '('
                i += 1
            else:
                raise ValueError(f"Неизвестный токен: {token}")

        while operators:
            self._apply_operation(values, operators)

        if len(values) != 1:
            raise ValueError("Некорректное выражение")

        return values[0]

    def _is_number(self, token):
        try:
            self._parse_number(token)
            return True
        except:
            return False

    def _parse_number(self, token):

        special_values = {
            'INF': math.inf,
            'NEG_INF': -math.inf,
            'NAN': math.nan
        }
        if token in special_values:
            return special_values[token]

        try:
            return float(token)
        except ValueError:
            raise ValueError(f"Некорректное число: {token}")

    #приоритет бинарных операций
    def _get_priority(self, operator):
        priorities = {
            '^': 3,
            '*': 2,
            '/': 2,
            '+': 1,
            '-': 1
        }
        return priorities.get(operator, 0)

    def _apply_operation(self, values, operators):
        if len(values) < 2 or not operators:
            raise ValueError("Некорректное выражение")

        operator = operators.pop()
        b = values.pop()
        a = values.pop()

        if math.isnan(a) or math.isnan(b):
            values.append(math.nan)
            return

        try:
            result = self._handle_uncertainties(a, b, operator)
            if result is not None:
                values.append(result)
                return

            if operator == '+':
                result = a + b
            elif operator == '-':
                result = a - b
            elif operator == '*':
                result = a * b
            elif operator == '/':
                if b == 0:
                    result = math.nan
                else:
                    result = a / b
            elif operator == '^':
                result = a ** b
            else:
                raise ValueError(f"Неизвестный оператор: {operator}")

            values.append(result)

        except OverflowError:
            #обработка переполнения
            sign = 1 if a > 0 else -1
            if operator == '^' and b > 0:
                values.append(math.inf * sign)
            else:
                values.append(math.inf if a > 0 else -math.inf)
        except Exception as e:
            raise ValueError(f"Ошибка вычисления: {str(e)}")

    def _handle_uncertainties(self, a, b, operator):


        a_is_inf = math.isinf(a)
        b_is_inf = math.isinf(b)

        if operator == '+':
            if a_is_inf and b_is_inf:
                if a == b:
                    return a
                else:
                    return math.nan

        elif operator == '-':
            if a_is_inf and b_is_inf:
                if a == b:
                    return math.nan
                else:
                    return math.inf if a > b else -math.inf

        elif operator == '*':
            if (a == 0 and b_is_inf) or (a_is_inf and b == 0):
                return math.nan

            if a_is_inf or b_is_inf:
                if a == 0 or b == 0:
                    return math.nan
                # Определяем знак результата
                sign_a = 1 if a >= 0 else -1
                sign_b = 1 if b >= 0 else -1
                sign = sign_a * sign_b
                return math.inf if sign > 0 else -math.inf

        elif operator == '/':
            if a_is_inf and b_is_inf:
                return math.nan

            if b == 0:
                return math.nan

            if a_is_inf:
                sign_a = 1 if a >= 0 else -1
                sign_b = 1 if b >= 0 else -1
                sign = sign_a * sign_b
                return math.inf if sign > 0 else -math.inf

            if b_is_inf:
                return 0.0

        elif operator == '^':
            if a == 0 and b == 0:
                return math.nan
            if b_is_inf:
                return math.nan
            if a_is_inf and b == 0:
                return math.nan

            if a_is_inf:
                if b > 0:
                    return math.inf if a > 0 else -math.inf
                elif b < 0:
                    return 0.0
                else:
                    return 1.0

            if b_is_inf:
                if abs(a) > 1:
                    return math.inf if a > 0 else -math.inf
                elif abs(a) < 1:
                    return 0.0
                else:
                    return math.nan


        return None


def safe_isnan(value):
    try:
        return math.isnan(value)
    except (TypeError, ValueError):
        return False


def safe_isinf(value):
    try:
        return math.isinf(value)
    except (TypeError, ValueError):
        return False


def format_result(result):
    if isinstance(result, str):
        return result

    if safe_isnan(result):
        return "nan"
    elif safe_isinf(result):
        return "inf" if result > 0 else "-inf"
    else:
        if isinstance(result, float) and result.is_integer():
            return int(result)
        return result


def main():
    calc = Calculator()

    print("Добро пожаловать в калькулятор!")
    print("Поддерживаются операции: +, -, *, /, ^ ")
    print("Специальные значения: +inf, inf, -inf, nan")
    print("Символ '_' содержит предыдущий результат")
    print("Введите 'exit' для выхода")
    print("-" * 50)

    while True:
        try:
            user_input = input("\nВведите выражение: ").strip()
            if user_input.lower() in ['quit', 'exit', 'выход']:
                break

            result = calc.calculate(user_input)
            formatted_result = format_result(result)
            print(f"Результат: {formatted_result}")

        except KeyboardInterrupt:
            print("\nВыход из программы.")
            break
        except Exception as e:
            print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
