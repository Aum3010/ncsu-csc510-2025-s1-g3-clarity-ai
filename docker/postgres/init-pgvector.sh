#!/bin/bash
set -e

# Initialize pgvector extension and optimizations
# This script runs after PostgreSQL is initialized

echo "Initializing pgvector extension for Clarity AI database..."

# Wait for PostgreSQL to be ready
until pg_isready -U "$POSTGRES_USER"; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

# Set up pgvector for the clarity_ai database only
echo "Setting up pgvector for Clarity AI database: ${APP_POSTGRES_DB:-clarity_ai}"

# Note: We use POSTGRES_USER (superuser) to create extensions, then grant to APP_POSTGRES_USER
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${APP_POSTGRES_DB:-clarity_ai}" <<-EOSQL
    -- Enable required extensions for Clarity AI
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS vector;
    
    -- Verify vector extension is loaded
    SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
    
    -- Set optimal pgvector parameters
    -- These settings optimize for 1536-dimensional embeddings (OpenAI ada-002)
    ALTER SYSTEM SET ivfflat.probes = 10;
    
    -- Reload configuration
    SELECT pg_reload_conf();
    
    -- Test vector operations
    DO \$\$
    BEGIN
        PERFORM '[1,2,3]'::vector;
        RAISE NOTICE 'Vector extension is working correctly in clarity_ai database';
    EXCEPTION
        WHEN OTHERS THEN
            RAISE EXCEPTION 'Vector extension test failed: %', SQLERRM;
    END
    \$\$;
    
    -- Show current vector-related settings
    SHOW shared_preload_libraries;
    
    -- Create performance monitoring view
    CREATE OR REPLACE VIEW vector_index_stats AS
    SELECT 
        schemaname,
        relname as tablename,
        indexrelname as indexname,
        pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
        idx_scan,
        idx_tup_read,
        idx_tup_fetch
    FROM pg_stat_user_indexes 
    WHERE indexrelname LIKE '%vector%' OR indexrelname LIKE '%embedding%';
    
    COMMENT ON VIEW vector_index_stats IS 'Monitor vector index usage and performance';
    
    -- Grant permissions to clarity_user (APP_POSTGRES_USER)
    -- Note: The user should already exist from 01-init-db.sql
    DO \$\$
    BEGIN
        -- Grant schema usage
        EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', '${APP_POSTGRES_USER:-clarity_user}');
        
        -- Grant all privileges on existing tables
        EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', '${APP_POSTGRES_USER:-clarity_user}');
        
        -- Grant all privileges on existing sequences
        EXECUTE format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %I', '${APP_POSTGRES_USER:-clarity_user}');
        
        -- Grant default privileges for future objects
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO %I', '${APP_POSTGRES_USER:-clarity_user}');
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO %I', '${APP_POSTGRES_USER:-clarity_user}');
        
        RAISE NOTICE 'Granted all permissions to user: ${APP_POSTGRES_USER:-clarity_user}';
    END
    \$\$;
EOSQL

echo "pgvector initialization completed for clarity_ai database!"

# Set up automatic maintenance job (if needed)
cat > /tmp/maintenance.sql <<EOF
-- Maintenance queries for vector indexes
-- Run these periodically for optimal performance

-- Analyze tables with vector columns
ANALYZE documents;

-- Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY document_stats;

-- Check vector index statistics
SELECT * FROM vector_index_stats;
EOF

echo "Maintenance SQL script created at /tmp/maintenance.sql"
echo "pgvector setup complete!"