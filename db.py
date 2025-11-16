from dataclasses import dataclass

# Represents the actual and expected number of rows affected by a write to the database
@dataclass
class DBWrite:
    actual: int
    expected: int

# Example:
# For 
# `parameter_count = 2`
# this function returns
# `"(? , ?)"`
def create_placeholders_string(parameter_count: int) -> str:
    placeholders = f"({', '.join(['?'] * parameter_count)})"

    return placeholders
