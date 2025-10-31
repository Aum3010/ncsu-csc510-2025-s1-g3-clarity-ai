"""
Test script for database optimization features.

This script tests the database optimization utilities without requiring
a full database connection.
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))


def test_connection_pool_config():
    """Test connection pool configuration."""
    print("Testing connection pool configuration...")
    
    from database_optimization import get_connection_pool_config
    
    # Set test environment variables
    os.environ['DB_POOL_SIZE'] = '15'
    os.environ['DB_MAX_OVERFLOW'] = '25'
    os.environ['DB_POOL_RECYCLE'] = '7200'
    
    config = get_connection_pool_config()
    
    assert config['pool_size'] == 15, f"Expected pool_size=15, got {config['pool_size']}"
    assert config['max_overflow'] == 25, f"Expected max_overflow=25, got {config['max_overflow']}"
    assert config['pool_recycle'] == 7200, f"Expected pool_recycle=7200, got {config['pool_recycle']}"
    assert config['pool_pre_ping'] == True, f"Expected pool_pre_ping=True, got {config['pool_pre_ping']}"
    
    print("✓ Connection pool configuration test passed")
    return True


def test_query_monitor():
    """Test query performance monitor."""
    print("\nTesting query performance monitor...")
    
    from database_optimization import QueryPerformanceMonitor
    
    monitor = QueryPerformanceMonitor(slow_query_threshold=0.5)
    
    # Test initial state
    stats = monitor.get_stats()
    assert stats['total_slow_queries'] == 0, "Expected 0 slow queries initially"
    assert stats['average_duration'] == 0, "Expected 0 average duration initially"
    
    # Simulate slow queries
    monitor.query_stats.append({
        'statement': 'SELECT * FROM test',
        'parameters': {},
        'duration': 1.5,
        'timestamp': 1234567890
    })
    monitor.query_stats.append({
        'statement': 'SELECT * FROM test2',
        'parameters': {},
        'duration': 2.0,
        'timestamp': 1234567891
    })
    
    stats = monitor.get_stats()
    assert stats['total_slow_queries'] == 2, f"Expected 2 slow queries, got {stats['total_slow_queries']}"
    assert stats['average_duration'] == 1.75, f"Expected average 1.75s, got {stats['average_duration']}"
    assert stats['max_duration'] == 2.0, f"Expected max 2.0s, got {stats['max_duration']}"
    
    # Test clear
    monitor.clear_stats()
    stats = monitor.get_stats()
    assert stats['total_slow_queries'] == 0, "Expected 0 slow queries after clear"
    
    print("✓ Query performance monitor test passed")
    return True


def test_optimize_query_decorator():
    """Test the optimize_query decorator."""
    print("\nTesting optimize_query decorator...")
    
    from database_optimization import optimize_query
    import time
    
    @optimize_query("Test query")
    def test_function():
        time.sleep(0.1)
        return "result"
    
    result = test_function()
    assert result == "result", f"Expected 'result', got {result}"
    
    print("✓ Optimize query decorator test passed")
    return True


def test_migration_file():
    """Test that the migration file is valid."""
    print("\nTesting migration file...")
    
    import importlib.util
    import sys
    
    migration_path = os.path.join(
        os.path.dirname(__file__),
        'migrations/versions/h3i4j5k6l7m8_optimize_database_queries.py'
    )
    
    try:
        # Load the migration module
        spec = importlib.util.spec_from_file_location("migration", migration_path)
        migration = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules to handle imports
        sys.modules['migration'] = migration
        
        # Execute the module to load its contents
        spec.loader.exec_module(migration)
        
        # Check that required functions exist
        assert hasattr(migration, 'upgrade'), "Migration missing upgrade function"
        assert hasattr(migration, 'downgrade'), "Migration missing downgrade function"
        
        # Check that functions are callable
        assert callable(migration.upgrade), "upgrade is not callable"
        assert callable(migration.downgrade), "downgrade is not callable"
        
        # Check revision identifiers
        assert migration.revision == 'h3i4j5k6l7m8', f"Unexpected revision: {migration.revision}"
        assert migration.down_revision == 'd4f83cc841e9', f"Unexpected down_revision: {migration.down_revision}"
        
        print("✓ Migration file test passed")
        return True
        
    except ImportError as e:
        # If alembic is not installed, just verify the file exists and has basic structure
        print(f"  Note: Alembic not available ({e}), performing basic validation...")
        
        # Read the file and check for required content
        with open(migration_path, 'r') as f:
            content = f.read()
        
        # Check for required elements
        assert 'def upgrade():' in content, "Migration missing upgrade function definition"
        assert 'def downgrade():' in content, "Migration missing downgrade function definition"
        assert "revision = 'h3i4j5k6l7m8'" in content, "Missing or incorrect revision ID"
        assert "down_revision = 'd4f83cc841e9'" in content, "Missing or incorrect down_revision"
        
        print("✓ Migration file test passed (basic validation)")
        return True


def main():
    """Run all tests."""
    print("="*60)
    print("Database Optimization Tests")
    print("="*60)
    
    tests = [
        test_connection_pool_config,
        test_query_monitor,
        test_optimize_query_decorator,
        test_migration_file,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {test.__name__}")
            print(f"  Error: {str(e)}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
