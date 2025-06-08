from typing import Any, List, Literal, Optional

from pydantic import BaseModel
from pydantic.config import JsonValue
from typing_extensions import TypedDict

Operator = Literal["gt", "ge", "lt", "le", "eq", "not_eq", "in", "not_in"]


class Condition(TypedDict):
    field: str
    operator: Operator
    value: Any


class ValidationMessage(TypedDict):
    message: str


class ThenClause(TypedDict):
    field: str
    rule: ValidationMessage


class CrossFieldRule(BaseModel):
    conditions: List[Condition]
    then: ThenClause


class ValidationRuleBuilder:

    def __init__(self) -> None:
        self._if_conditions: List[Condition] = []
        self._then_rule: Optional[ThenClause] = None

    def addIf(
        self, field: str, operator: Operator, value: Any
    ) -> "ValidationRuleBuilder":
        """
        Add an 'if' condition. If value is a string prefixed with '$', it indicates that the
        value should be taken from another field.
        """
        self._if_conditions.append(
            {
                "field": field,
                "operator": operator,
                "value": value,
            }
        )
        return self

    def addThen(self, field: str, message: str) -> "ValidationRuleBuilder":
        """
        Define the 'then' rule that produces an error message for the given field.
        """
        self._then_rule = {
            "field": field,
            "rule": {
                "message": message,
            },
        }
        return self

    def build(self) -> CrossFieldRule:
        """
        Build and return the complete cross-field validation rule.
        """
        if not self._if_conditions:
            raise ValueError("At least one 'if' condition must be defined.")
        if self._then_rule is None:
            raise ValueError("A 'then' rule must be defined.")
        return CrossFieldRule(conditions=self._if_conditions, then=self._then_rule)


class Validator:
    def __init__(self) -> None:
        self._rules: List[CrossFieldRule] = []

    def addRule(self, rule: CrossFieldRule) -> "Validator":
        """
        Add a cross-field rule.
        """
        self._rules.append(rule)
        return self

    def build(self) -> "Validator":
        """
        Finalize the building of the validator. (Returns itself for fluent-style chaining.)
        """
        return self

    def dict(self) -> List[JsonValue]:
        """
        Return a list of all cross-field validation rules.
        """

        return [rule.model_dump(mode="json") for rule in self._rules]

    def validate(self, obj: Any) -> None:
        """
        Validate an object (such as a Pydantic model). For each rule, if all "conditions" conditions are met,
        an error message is recorded. If any error exists, a ValueError is raised with a dictionary of errors.
        """

        for rule in self._rules:
            conditions: List[Condition] = rule.conditions
            then_clause: ThenClause = rule.then

            all_conditions_pass = True
            for cond in conditions:
                field: str = cond["field"]
                operator: Operator = cond["operator"]
                expected_value: Any = cond["value"]

                if isinstance(expected_value, str) and expected_value.startswith("$"):
                    ref_field = expected_value[1:]
                    expected_value = getattr(obj, ref_field, None)

                actual_value: Any = getattr(obj, field, None)

                if not self._eval(actual_value, operator, expected_value):
                    all_conditions_pass = False
                    break

            if all_conditions_pass:
                error_field: str = then_clause["field"]
                message: str = then_clause["rule"]["message"]
                raise ValueError(f"Invalid {error_field}: {message}")

    def _eval(self, actual: Any, operator: Operator, expected: Any) -> bool:
        """
        Evaluate a condition between an actual value and an expected value using the provided operator.
        """
        if operator == "gt":
            return actual > expected
        elif operator == "ge":
            return actual >= expected
        elif operator == "lt":
            return actual < expected
        elif operator == "le":
            return actual <= expected
        elif operator == "eq":
            return actual == expected
        elif operator == "not_eq":
            return actual != expected
        elif operator == "in":
            return actual in expected
        elif operator == "not_in":
            return actual not in expected
        else:
            raise ValueError(f"Unsupported operator: {operator}")
