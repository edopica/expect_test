#!/usr/bin/env python3
"""
Demo script showing conflict detection and resolution
"""

from expect_test import expect, set_conflict_resolution, ConflictResolution
import random

# First, let's create a function that produces different output
def get_random_data(seed=None):
    if seed:
        random.seed(seed)
    return {
        "value": random.randint(1, 100),
        "list": [random.randint(1, 10) for _ in range(3)]
    }

# Test that will produce consistent output first time
@expect("random_test_demo")
def test_random():
    return get_random_data(seed=42)  # Fixed seed for first run

# Run it first time to create snapshot
print("First run - creating snapshot:")
test_random()

# Now change the function to produce different output
@expect("random_test_demo")
def test_random_modified():
    return get_random_data(seed=99)  # Different seed = different output

# This will detect a conflict
print("\nSecond run - detecting conflict (with FAIL mode):")
set_conflict_resolution(ConflictResolution.FAIL)

try:
    test_random_modified()
except AssertionError as e:
    print(f"✗ Test failed as expected: {e}")

print("\nNow with ACCEPT_NEW mode:")
set_conflict_resolution(ConflictResolution.ACCEPT_NEW)
test_random_modified()

print("\nFinal run to verify new value is stored:")
test_random_modified()
