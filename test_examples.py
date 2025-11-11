"""
Example usage of the expect_test library
"""

from expect_test import (
    expect, 
    expect_inline, 
    set_conflict_resolution,
    auto_accept,
    ConflictResolution
)
import json


# Example 1: Simple function testing
def fibonacci(n):
    """Calculate fibonacci number"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


@expect("fibonacci_15")
def test_fibonacci_basic():
    """Test fibonacci calculation"""
    return fibonacci(15)


@expect("fibonacci_sequence")
def test_fibonacci_sequence():
    """Test fibonacci sequence"""
    return [fibonacci(i) for i in range(10)]


# Example 2: Testing with complex objects
class OrderBook:
    def __init__(self):
        self.buys = []
        self.sells = []
        
    def add_order(self, side, price, size):
        order = {"price": price, "size": size}
        if side == "buy":
            self.buys.append(order)
            self.buys.sort(key=lambda x: -x["price"])  # Sort descending
        else:
            self.sells.append(order)
            self.sells.sort(key=lambda x: x["price"])  # Sort ascending
    
    def to_dict(self):
        return {
            "buys": self.buys,
            "sells": self.sells,
            "spread": self.get_spread()
        }
    
    def get_spread(self):
        if self.buys and self.sells:
            return self.sells[0]["price"] - self.buys[0]["price"]
        return None


@expect("orderbook_simple")
def test_orderbook():
    """Test order book state after adding orders"""
    book = OrderBook()
    book.add_order("buy", 100.0, 10)
    book.add_order("buy", 99.5, 20)
    book.add_order("sell", 101.0, 15)
    book.add_order("sell", 102.0, 5)
    return book.to_dict()


# Example 3: Testing with inline capture
def test_inline_example():
    """Demonstrate inline expect testing"""
    with expect_inline("inline_calculation") as e:
        result = {
            "sum": sum(range(100)),
            "product": 5 * 6 * 7,
            "list": list(range(5))
        }
        e.capture(result)


# Example 4: Testing exceptions
@expect("division_by_zero")
def test_exception():
    """Test that captures an exception"""
    return 10 / 0  # This will raise ZeroDivisionError


# Example 5: Table-style testing (like the article)
def round_special(n, precision=2):
    """Custom rounding function"""
    # Contrived example with some edge cases
    if n == 0:
        return 0.0
    elif abs(n) < 0.01:
        return 0.0
    else:
        factor = 10 ** precision
        return round(n * factor) / factor


@expect("rounding_table")
def test_rounding_table():
    """Test rounding function with multiple examples"""
    test_cases = [0, 0.001, 0.009, 0.01, 0.5, 1.234, 1.235, 1.236, 10.999]
    
    results = []
    for n in test_cases:
        results.append({
            "input": n,
            "output": round_special(n),
            "precision_3": round_special(n, precision=3)
        })
    
    # Format as a nice table-like structure
    return {
        "test_cases": results,
        "summary": f"Tested {len(test_cases)} values"
    }


# Example 6: Testing stateful operations
class Counter:
    def __init__(self):
        self.value = 0
        self.history = []
    
    def increment(self, by=1):
        self.value += by
        self.history.append(("increment", by, self.value))
    
    def decrement(self, by=1):
        self.value -= by
        self.history.append(("decrement", by, self.value))
    
    def reset(self):
        self.value = 0
        self.history.append(("reset", 0, self.value))


@expect("counter_operations")
def test_counter():
    """Test counter with multiple operations"""
    counter = Counter()
    counter.increment(5)
    counter.increment(3)
    counter.decrement(2)
    counter.increment()
    counter.reset()
    counter.increment(10)
    
    return {
        "final_value": counter.value,
        "history": counter.history,
        "operation_count": len(counter.history)
    }


# Example 7: Testing with configuration changes
def test_with_auto_accept():
    """Example of using auto-accept mode"""
    # This would automatically accept any changes without prompting
    auto_accept(True)
    
    @expect("auto_accept_test")
    def test():
        import random
        random.seed(42)  # For reproducibility
        return {
            "random_numbers": [random.randint(1, 100) for _ in range(5)],
            "timestamp": "2024-01-01T00:00:00"  # Fixed for testing
        }
    
    result = test()
    
    # Reset to interactive mode
    set_conflict_resolution(ConflictResolution.INTERACTIVE)
    return result


# Example 8: Nested data structures
@expect("nested_structure")
def test_nested_data():
    """Test with deeply nested data structures"""
    return {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "permissions": ["read", "write"],
                "metadata": {
                    "created": "2024-01-01",
                    "last_login": "2024-01-15",
                    "settings": {
                        "theme": "dark",
                        "notifications": True
                    }
                }
            },
            {
                "id": 2,
                "name": "Bob",
                "permissions": ["read"],
                "metadata": {
                    "created": "2024-01-02",
                    "last_login": "2024-01-14",
                    "settings": {
                        "theme": "light",
                        "notifications": False
                    }
                }
            }
        ],
        "system": {
            "version": "1.0.0",
            "features": ["auth", "api", "websocket"]
        }
    }


# Main execution
if __name__ == "__main__":
    print("Running expect tests...\n")
    
    # Set the conflict resolution mode
    # Options: INTERACTIVE (default), ACCEPT_NEW, KEEP_OLD, FAIL
    # set_conflict_resolution(ConflictResolution.INTERACTIVE)
    
    # Run all tests
    test_fibonacci_basic()
    test_fibonacci_sequence()
    test_orderbook()
    test_inline_example()
    
    # This will capture the exception
    try:
        test_exception()
    except:
        pass  # Exception is captured in snapshot
    
    test_rounding_table()
    test_counter()
    test_nested_data()
    
    # Optionally test with auto-accept
    # test_with_auto_accept()
    
    print("\nAll tests completed!")
    print("Check .expect_snapshots/ directory for snapshot files")
