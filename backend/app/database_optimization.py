"""
Database Optimization Utilities

Provides utilities for database query optimization, performance monitoring,
and connection pooling configuration.
"""

import os
import time
from functools import wraps
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

try:
    from .main import db
except ImportError:
    # For standalone testing
    db = None


# Connection pooling configuration
def get_connection_pool_config() -> Dict[str, Any]:
    """
    Get connection pooling configuration from environment variables.
    
    Returns:
        Dictionary with SQLAlchemy engine options for connection pooling
    """
    return {
        # Pool size: number of connections to maintain
        'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
        
        # Max overflow: additional connections beyond pool_size
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
        
        # Pool recycle: recycle connections after this many seconds (prevents stale connections)
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
        
        # Pool pre-ping: test connections before using them
        'pool_pre_ping': os.getenv('DB_POOL_PRE_PING', 'true').lower() == 'true',
        
        # Pool timeout: seconds to wait for a connection from the pool
        'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30')),
        
        # Echo pool: log pool checkouts/checkins (useful for debugging)
        'echo_pool': os.getenv('DB_ECHO_POOL', 'false').lower() == 'true',
    }


def configure_connection_pooling(app):
    """
    Configure SQLAlchemy connection pooling for the Flask app.
    
    Args:
        app: Flask application instance
    """
    pool_config = get_connection_pool_config()
    
    # Update app config with engine options
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'poolclass': QueuePool,
        'pool_size': pool_config['pool_size'],
        'max_overflow': pool_config['max_overflow'],
        'pool_recycle': pool_config['pool_recycle'],
        'pool_pre_ping': pool_config['pool_pre_ping'],
        'pool_timeout': pool_config['pool_timeout'],
        'echo_pool': pool_config['echo_pool'],
    }
    
    print(f"Database connection pooling configured:")
    print(f"  - Pool size: {pool_config['pool_size']}")
    print(f"  - Max overflow: {pool_config['max_overflow']}")
    print(f"  - Pool recycle: {pool_config['pool_recycle']}s")
    print(f"  - Pool pre-ping: {pool_config['pool_pre_ping']}")


# Query performance monitoring
class QueryPerformanceMonitor:
    """
    Monitor and log slow database queries.
    """
    
    def __init__(self, slow_query_threshold: float = 1.0):
        """
        Initialize the query performance monitor.
        
        Args:
            slow_query_threshold: Threshold in seconds for logging slow queries
        """
        self.slow_query_threshold = slow_query_threshold
        self.query_stats: List[Dict] = []
        self.enabled = os.getenv('DB_QUERY_MONITORING', 'false').lower() == 'true'
    
    def setup_monitoring(self, engine: Engine):
        """
        Set up query monitoring on the SQLAlchemy engine.
        
        Args:
            engine: SQLAlchemy engine instance
        """
        if not self.enabled:
            return
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - conn.info['query_start_time'].pop()
            
            if total_time > self.slow_query_threshold:
                self._log_slow_query(statement, parameters, total_time)
                self.query_stats.append({
                    'statement': statement,
                    'parameters': parameters,
                    'duration': total_time,
                    'timestamp': time.time()
                })
    
    def _log_slow_query(self, statement: str, parameters: Any, duration: float):
        """Log a slow query."""
        print(f"\n⚠️  SLOW QUERY DETECTED ({duration:.3f}s)")
        print(f"Statement: {statement[:200]}...")
        if parameters:
            print(f"Parameters: {parameters}")
        print()
    
    def get_stats(self) -> Dict:
        """Get query performance statistics."""
        if not self.query_stats:
            return {
                'total_slow_queries': 0,
                'average_duration': 0,
                'max_duration': 0
            }
        
        durations = [q['duration'] for q in self.query_stats]
        return {
            'total_slow_queries': len(self.query_stats),
            'average_duration': sum(durations) / len(durations),
            'max_duration': max(durations),
            'recent_queries': self.query_stats[-10:]  # Last 10 slow queries
        }
    
    def clear_stats(self):
        """Clear collected statistics."""
        self.query_stats.clear()


# Global query monitor instance
query_monitor = QueryPerformanceMonitor(
    slow_query_threshold=float(os.getenv('SLOW_QUERY_THRESHOLD', '1.0'))
)


# Query analysis utilities
@contextmanager
def explain_analyze(query_description: str = "Query"):
    """
    Context manager to run EXPLAIN ANALYZE on queries within the block.
    
    Usage:
        with explain_analyze("Get user requirements"):
            requirements = Requirement.query.filter_by(owner_id=user_id).all()
    
    Args:
        query_description: Description of the query being analyzed
    """
    # Enable query echoing temporarily
    original_echo = db.engine.echo
    db.engine.echo = True
    
    print(f"\n{'='*60}")
    print(f"EXPLAIN ANALYZE: {query_description}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"Query completed in {duration:.3f}s")
        print(f"{'='*60}\n")
        
        # Restore original echo setting
        db.engine.echo = original_echo


def analyze_query_plan(query_sql: str, params: Optional[Dict] = None) -> Dict:
    """
    Run EXPLAIN ANALYZE on a raw SQL query and return the execution plan.
    
    Args:
        query_sql: SQL query to analyze
        params: Optional parameters for the query
    
    Returns:
        Dictionary with query plan information
    """
    try:
        # Prepare EXPLAIN ANALYZE query
        explain_query = f"EXPLAIN ANALYZE {query_sql}"
        
        # Execute and fetch results
        result = db.session.execute(text(explain_query), params or {})
        plan_lines = [row[0] for row in result]
        
        # Parse execution time from plan
        execution_time = None
        for line in plan_lines:
            if 'Execution Time:' in line or 'Execution time:' in line:
                # Extract time value
                parts = line.split(':')
                if len(parts) > 1:
                    time_str = parts[1].strip().split()[0]
                    execution_time = float(time_str)
        
        return {
            'query': query_sql,
            'plan': '\n'.join(plan_lines),
            'execution_time_ms': execution_time,
            'success': True
        }
    
    except Exception as e:
        return {
            'query': query_sql,
            'error': str(e),
            'success': False
        }


def get_table_statistics() -> Dict:
    """
    Get statistics about database tables (row counts, sizes, etc.).
    
    Returns:
        Dictionary with table statistics
    """
    try:
        # Query to get table sizes and row counts
        query = text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes,
                n_live_tup AS row_count
            FROM pg_stat_user_tables
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """)
        
        result = db.session.execute(query)
        tables = []
        
        for row in result:
            tables.append({
                'schema': row[0],
                'table': row[1],
                'size': row[2],
                'size_bytes': row[3],
                'row_count': row[4]
            })
        
        return {
            'tables': tables,
            'total_tables': len(tables),
            'success': True
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'success': False
        }


def get_index_usage_statistics() -> Dict:
    """
    Get statistics about index usage to identify unused or inefficient indexes.
    
    Returns:
        Dictionary with index usage statistics
    """
    try:
        # Query to get index usage stats
        query = text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan AS index_scans,
                idx_tup_read AS tuples_read,
                idx_tup_fetch AS tuples_fetched,
                pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
            FROM pg_stat_user_indexes
            ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC;
        """)
        
        result = db.session.execute(query)
        indexes = []
        
        for row in result:
            indexes.append({
                'schema': row[0],
                'table': row[1],
                'index': row[2],
                'scans': row[3],
                'tuples_read': row[4],
                'tuples_fetched': row[5],
                'size': row[6]
            })
        
        # Identify potentially unused indexes (0 scans)
        unused_indexes = [idx for idx in indexes if idx['scans'] == 0]
        
        return {
            'indexes': indexes,
            'total_indexes': len(indexes),
            'unused_indexes': unused_indexes,
            'unused_count': len(unused_indexes),
            'success': True
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'success': False
        }


def get_connection_pool_stats() -> Dict:
    """
    Get current connection pool statistics.
    
    Returns:
        Dictionary with connection pool statistics
    """
    try:
        pool = db.engine.pool
        
        return {
            'pool_size': pool.size(),
            'checked_in_connections': pool.checkedin(),
            'checked_out_connections': pool.checkedout(),
            'overflow_connections': pool.overflow(),
            'total_connections': pool.size() + pool.overflow(),
            'success': True
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'success': False
        }


# Decorator for query optimization
def optimize_query(description: str = "Query"):
    """
    Decorator to monitor and optimize query performance.
    
    Usage:
        @optimize_query("Get user requirements")
        def get_user_requirements(user_id):
            return Requirement.query.filter_by(owner_id=user_id).all()
    
    Args:
        description: Description of the query being optimized
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log if slow
                if duration > query_monitor.slow_query_threshold:
                    print(f"⚠️  Slow operation: {description} took {duration:.3f}s")
                
                return result
            
            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ Query failed: {description} after {duration:.3f}s - {str(e)}")
                raise
        
        return wrapper
    return decorator


# Eager loading helpers
def get_requirements_with_relations(owner_id: str):
    """
    Get requirements with eager loading of related data.
    Optimized to reduce N+1 query problems.
    
    Args:
        owner_id: User ID to filter requirements
    
    Returns:
        List of Requirement objects with preloaded relationships
    """
    from .models import Requirement
    
    return Requirement.query.filter_by(owner_id=owner_id).options(
        db.joinedload(Requirement.tags),
        db.joinedload(Requirement.source_document),
        db.joinedload(Requirement.ambiguity_analyses)
    ).all()


def get_analysis_with_terms(analysis_id: int, owner_id: Optional[str] = None):
    """
    Get ambiguity analysis with eager loading of terms and clarifications.
    Optimized to reduce N+1 query problems.
    
    Args:
        analysis_id: Analysis ID
        owner_id: Optional user ID for authorization
    
    Returns:
        AmbiguityAnalysis object with preloaded relationships
    """
    from .models import AmbiguityAnalysis, AmbiguousTerm, ClarificationHistory
    
    query = AmbiguityAnalysis.query.filter_by(id=analysis_id)
    
    if owner_id:
        query = query.filter_by(owner_id=owner_id)
    
    return query.options(
        db.joinedload(AmbiguityAnalysis.terms).joinedload(AmbiguousTerm.clarifications),
        db.joinedload(AmbiguityAnalysis.requirement)
    ).first()


def get_analyses_for_requirements(requirement_ids: List[int], owner_id: Optional[str] = None):
    """
    Get all analyses for multiple requirements with eager loading.
    Optimized for batch operations.
    
    Args:
        requirement_ids: List of requirement IDs
        owner_id: Optional user ID for authorization
    
    Returns:
        List of AmbiguityAnalysis objects with preloaded relationships
    """
    from .models import AmbiguityAnalysis, AmbiguousTerm
    
    query = AmbiguityAnalysis.query.filter(
        AmbiguityAnalysis.requirement_id.in_(requirement_ids)
    )
    
    if owner_id:
        query = query.filter_by(owner_id=owner_id)
    
    return query.options(
        db.joinedload(AmbiguityAnalysis.terms).joinedload(AmbiguousTerm.clarifications),
        db.joinedload(AmbiguityAnalysis.requirement)
    ).order_by(AmbiguityAnalysis.analyzed_at.desc()).all()
