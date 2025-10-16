#!/usr/bin/env python3
"""
Simple Calculator Program
Provides basic arithmetic operations with proper error handling.
"""

def add(a, b):
    """Add two numbers and return the result."""
    return a + b

def subtract(a, b):
    """Subtract b from a and return the result."""
    return a - b

def multiply(a, b):
    """Multiply two numbers and return the result."""
    return a * b

def divide(a, b):
    """
    Divide a by b and return the result.
    Raises ZeroDivisionError if b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b

def main():
    """Demonstrate all calculator operations."""
    print("Simple Calculator Demo")
    print("=" * 25)

    # Test values
    x, y = 10, 5
    print(f"Using test values: x = {x}, y = {y}")
    print()

    # Addition
    result = add(x, y)
    print(f"Addition: {x} + {y} = {result}")

    # Subtraction
    result = subtract(x, y)
    print(f"Subtraction: {x} - {y} = {result}")

    # Multiplication
    result = multiply(x, y)
    print(f"Multiplication: {x} * {y} = {result}")

    # Division
    try:
        result = divide(x, y)
        print(f"Division: {x} / {y} = {result}")
    except ZeroDivisionError as e:
        print(f"Division error: {e}")

    # Test division by zero
    print()
    print("Testing division by zero:")
    try:
        result = divide(x, 0)
        print(f"Division: {x} / 0 = {result}")
    except ZeroDivisionError as e:
        print(f"Division error: {e}")

    # Additional test cases
    print()
    print("Additional test cases:")
    test_cases = [
        (15.5, 2.5),
        (-10, 3),
        (0, 5),
        (7, -2)
    ]

    for a, b in test_cases:
        print(f"\nTest values: a = {a}, b = {b}")
        print(f"  {a} + {b} = {add(a, b)}")
        print(f"  {a} - {b} = {subtract(a, b)}")
        print(f"  {a} * {b} = {multiply(a, b)}")

        try:
            print(f"  {a} / {b} = {divide(a, b)}")
        except ZeroDivisionError as e:
            print(f"  Division error: {e}")

if __name__ == "__main__":
    main()