"""
Expect Test Framework for Python
A snapshot testing library inspired by Jane Street's expect tests.
"""

import json
import os
import sys
import hashlib
import difflib
import inspect
import functools
from pathlib import Path
from typing import Any, Callable, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    INTERACTIVE = "interactive"
    ACCEPT_NEW = "accept_new"
    KEEP_OLD = "keep_old"
    FAIL = "fail"


@dataclass
class TestSnapshot:
    """Represents a test snapshot"""
    name: str
    value: Any
    timestamp: str
    file_path: str
    line_number: int
    hash: str
    
    def to_dict(self):
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "hash": self.hash
        }


class ExpectTestConfig:
    """Global configuration for expect tests"""
    def __init__(self):
        self.snapshot_dir = ".expect_snapshots"
        self.conflict_resolution = ConflictResolution.INTERACTIVE
        self.auto_accept = False
        self.show_diffs = True
        self.ci_mode = os.environ.get("CI", "false").lower() == "true"
        
    def set_conflict_resolution(self, strategy: Union[ConflictResolution, str]):
        if isinstance(strategy, str):
            strategy = ConflictResolution(strategy)
        self.conflict_resolution = strategy


# Global config instance
config = ExpectTestConfig()


class SnapshotManager:
    """Manages snapshot storage and retrieval"""
    
    def __init__(self, snapshot_file: Optional[str] = None):
        self.snapshot_file = snapshot_file or self._get_default_snapshot_file()
        self.snapshots = self._load_snapshots()
        self.pending_updates = {}
        
    def _get_default_snapshot_file(self) -> str:
        """Get the default snapshot file path based on the calling test file"""
        frame = inspect.currentframe()
        for _ in range(10):  # Look up the stack
            frame = frame.f_back
            if frame is None:
                break
            filename = frame.f_code.co_filename
            if filename.endswith(".py") and not filename.endswith("expect_test.py"):
                base_name = Path(filename).stem
                snapshot_dir = Path(filename).parent / config.snapshot_dir
                snapshot_dir.mkdir(exist_ok=True)
                return str(snapshot_dir / f"{base_name}.json")
        
        # Fallback
        snapshot_dir = Path(config.snapshot_dir)
        snapshot_dir.mkdir(exist_ok=True)
        return str(snapshot_dir / "default_snapshots.json")
    
    def _load_snapshots(self) -> dict:
        """Load existing snapshots from file"""
        if os.path.exists(self.snapshot_file):
            try:
                with open(self.snapshot_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {self.snapshot_file}, starting fresh")
                return {}
        return {}
    
    def _save_snapshots(self):
        """Save snapshots to file"""
        # Merge pending updates
        self.snapshots.update(self.pending_updates)
        
        # Ensure directory exists
        Path(self.snapshot_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.snapshot_file, 'w') as f:
            json.dump(self.snapshots, f, indent=2, sort_keys=True, default=str)
        
        self.pending_updates.clear()
    
    def get_snapshot(self, test_name: str) -> Optional[Any]:
        """Get existing snapshot for a test"""
        if test_name in self.pending_updates:
            return self.pending_updates[test_name]["value"]
        if test_name in self.snapshots:
            return self.snapshots[test_name]["value"]
        return None
    
    def update_snapshot(self, test_name: str, value: Any, metadata: dict):
        """Update or create a snapshot"""
        snapshot_data = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            **metadata
        }
        self.pending_updates[test_name] = snapshot_data
    
    def has_snapshot(self, test_name: str) -> bool:
        """Check if snapshot exists"""
        return test_name in self.snapshots or test_name in self.pending_updates
    
    def commit_updates(self):
        """Commit all pending updates to disk"""
        if self.pending_updates:
            self._save_snapshots()


def _serialize_value(value: Any) -> Any:
    """Convert value to JSON-serializable format"""
    if value is None:
        return None
    elif isinstance(value, (str, int, float, bool)):
        return value
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif hasattr(value, '__dict__'):
        # For custom objects, try to convert to dict
        return _serialize_value(vars(value))
    else:
        # Fallback to string representation
        return str(value)


def _show_diff(old_value: Any, new_value: Any, test_name: str):
    """Display a colored diff between old and new values"""
    old_str = json.dumps(old_value, indent=2, sort_keys=True, default=str)
    new_str = json.dumps(new_value, indent=2, sort_keys=True, default=str)
    
    diff = difflib.unified_diff(
        old_str.splitlines(keepends=True),
        new_str.splitlines(keepends=True),
        fromfile=f"{test_name} (expected)",
        tofile=f"{test_name} (actual)",
        lineterm=''
    )
    
    # Color codes for terminal
    RED = '\033[91m'
    GREEN = '\033[92m'
    RESET = '\033[0m'
    
    print(f"\n{'='*60}")
    print(f"Diff for test: {test_name}")
    print('='*60)
    
    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            print(f"{GREEN}{line}{RESET}", end='')
        elif line.startswith('-') and not line.startswith('---'):
            print(f"{RED}{line}{RESET}", end='')
        else:
            print(line, end='')
    print(f"\n{'='*60}\n")


def _handle_conflict(test_name: str, old_value: Any, new_value: Any, 
                    manager: SnapshotManager, metadata: dict) -> bool:
    """
    Handle conflicts between existing and new snapshots.
    Returns True if the new value should be accepted.
    """
    if config.ci_mode:
        # In CI mode, always fail on conflicts
        return False
    
    if config.conflict_resolution == ConflictResolution.ACCEPT_NEW:
        return True
    elif config.conflict_resolution == ConflictResolution.KEEP_OLD:
        return False
    elif config.conflict_resolution == ConflictResolution.FAIL:
        raise AssertionError(f"Snapshot mismatch for test '{test_name}'")
    elif config.conflict_resolution == ConflictResolution.INTERACTIVE:
        if config.show_diffs:
            _show_diff(old_value, new_value, test_name)
        
        while True:
            response = input(f"Accept new snapshot for '{test_name}'? [y/n/d/q]: ").lower()
            if response == 'y':
                return True
            elif response == 'n':
                return False
            elif response == 'd':
                _show_diff(old_value, new_value, test_name)
            elif response == 'q':
                print("Quitting...")
                sys.exit(1)
            else:
                print("Invalid input. Use 'y' (yes), 'n' (no), 'd' (show diff), or 'q' (quit)")


def expect(test_name: str, snapshot_file: Optional[str] = None):
    """
    Decorator for expect tests.
    
    Args:
        test_name: Unique name for the test
        snapshot_file: Optional path to snapshot file (auto-detected if None)
    
    Usage:
        @expect("fibonacci_test")
        def test_fibonacci():
            return fibonacci(15)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get metadata about the test location
            frame = inspect.currentframe()
            metadata = {
                "file_path": frame.f_code.co_filename,
                "line_number": frame.f_lineno,
                "function_name": func.__name__
            }
            
            # Initialize snapshot manager
            manager = SnapshotManager(snapshot_file)
            
            # Execute the test function
            try:
                result = func(*args, **kwargs)
                serialized_result = _serialize_value(result)
            except Exception as e:
                # If test raises an exception, that's the result we snapshot
                serialized_result = {
                    "exception": str(type(e).__name__),
                    "message": str(e)
                }
            
            # Calculate hash for change detection
            result_hash = hashlib.md5(
                json.dumps(serialized_result, sort_keys=True, default=str).encode()
            ).hexdigest()
            metadata["hash"] = result_hash
            
            # Check if we have an existing snapshot
            if manager.has_snapshot(test_name):
                existing = manager.get_snapshot(test_name)
                
                if existing != serialized_result:
                    # Conflict: values differ
                    if _handle_conflict(test_name, existing, serialized_result, 
                                      manager, metadata):
                        manager.update_snapshot(test_name, serialized_result, metadata)
                        manager.commit_updates()
                        print(f"✓ Updated snapshot for '{test_name}'")
                    else:
                        # Fail the test
                        raise AssertionError(
                            f"Snapshot mismatch for test '{test_name}'\n"
                            f"Expected: {json.dumps(existing, indent=2)}\n"
                            f"Got: {json.dumps(serialized_result, indent=2)}"
                        )
                else:
                    print(f"✓ Test '{test_name}' passed")
            else:
                # No existing snapshot, create it
                manager.update_snapshot(test_name, serialized_result, metadata)
                manager.commit_updates()
                print(f"✓ Created new snapshot for '{test_name}'")
            
            return result
        
        return wrapper
    return decorator


def expect_inline(test_name: str):
    """
    Context manager for inline expect tests.
    
    Usage:
        with expect_inline("my_test") as e:
            result = some_function()
            e.capture(result)
    """
    class InlineExpectContext:
        def __init__(self, name: str):
            self.name = name
            self.manager = SnapshotManager()
            self.captured = None
            
        def capture(self, value: Any):
            """Capture a value for comparison"""
            self.captured = _serialize_value(value)
            
        def __enter__(self):
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.captured is None and exc_type is None:
                raise ValueError(f"No value captured for test '{self.name}'")
            
            # If an exception occurred, capture it
            if exc_type is not None:
                self.captured = {
                    "exception": str(exc_type.__name__),
                    "message": str(exc_val)
                }
            
            # Get metadata
            frame = inspect.currentframe()
            metadata = {
                "file_path": frame.f_code.co_filename,
                "line_number": frame.f_lineno,
                "hash": hashlib.md5(
                    json.dumps(self.captured, sort_keys=True, default=str).encode()
                ).hexdigest()
            }
            
            # Handle snapshot comparison
            if self.manager.has_snapshot(self.name):
                existing = self.manager.get_snapshot(self.name)
                if existing != self.captured:
                    if _handle_conflict(self.name, existing, self.captured, 
                                      self.manager, metadata):
                        self.manager.update_snapshot(self.name, self.captured, metadata)
                        self.manager.commit_updates()
                        print(f"✓ Updated snapshot for '{self.name}'")
                    else:
                        raise AssertionError(f"Snapshot mismatch for test '{self.name}'")
                else:
                    print(f"✓ Test '{self.name}' passed")
            else:
                self.manager.update_snapshot(self.name, self.captured, metadata)
                self.manager.commit_updates()
                print(f"✓ Created new snapshot for '{self.name}'")
            
            # Suppress any exception if we're capturing it
            if exc_type is not None:
                return True
    
    return InlineExpectContext(test_name)


# Utility functions for configuration
def set_conflict_resolution(strategy: Union[ConflictResolution, str]):
    """Set global conflict resolution strategy"""
    config.set_conflict_resolution(strategy)


def auto_accept(enabled: bool = True):
    """Enable/disable automatic acceptance of new snapshots"""
    config.auto_accept = enabled
    if enabled:
        config.conflict_resolution = ConflictResolution.ACCEPT_NEW


def set_snapshot_dir(directory: str):
    """Set the directory for snapshot files"""
    config.snapshot_dir = directory
