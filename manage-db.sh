#!/bin/bash


DB_CONTAINER="postgresql"
SUPERTOKENS_USER="supertokens_user"
SUPERTOKENS_DB="supertokens"
APP_USER="clarity_user"
APP_DB="clarity_ai"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo -e "${BLUE}Database Management for Clarity AI${NC}"
    echo "===================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo -e "${YELLOW}Setup Commands:${NC}"
    echo "  setup           Full database setup (start services, wait, test)"
    echo "  start           Start database services"
    echo "  stop            Stop database services"
    echo ""
    echo -e "${YELLOW}Connection Commands:${NC}"
    echo "  connect-app     Connect to Flask app database (clarity_ai)"
    echo "  connect-st      Connect to SuperTokens database"
    echo ""
    echo -e "${YELLOW}Management Commands:${NC}"
    echo "  status          Show database status and connections"
    echo "  logs            Show PostgreSQL logs"
    echo "  list-dbs        List all databases"
    echo ""
    echo -e "${YELLOW}Backup Commands:${NC}"
    echo "  backup-app      Backup Flask app database"
    echo "  restore-app     Restore Flask app database from backup"
    echo "  reset-app       Reset Flask app database (WARNING: deletes all data)"
    echo ""
    echo -e "${YELLOW}Other:${NC}"
    echo "  help            Show this help message"
    echo ""
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
        exit 1
    fi
}

# Function to check if container is running
check_container() {
    if ! docker ps | grep -q $DB_CONTAINER; then
        echo -e "${RED}❌ PostgreSQL container is not running.${NC}"
        echo "Run '$0 start' or 'docker compose up -d' to start it."
        exit 1
    fi
}

# Full database setup
setup_database() {
    check_docker
    
    echo -e "${BLUE}🚀 Setting up databases for Clarity AI...${NC}"
    
    # Start the services
    echo -e "${BLUE}📦 Starting PostgreSQL and SuperTokens services...${NC}"
    docker compose up -d
    
    # Wait for PostgreSQL to be ready
    echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
    sleep 10
    
    # Check if PostgreSQL is ready
    until docker exec $DB_CONTAINER pg_isready -U $SUPERTOKENS_USER > /dev/null 2>&1; do
        echo -e "${YELLOW}⏳ Waiting for PostgreSQL...${NC}"
        sleep 2
    done
    
    echo -e "${GREEN}✅ PostgreSQL is ready!${NC}"
    
    # Check if SuperTokens is ready
    echo -e "${YELLOW}⏳ Waiting for SuperTokens to be ready...${NC}"
    until curl -s http://localhost:3567/hello > /dev/null 2>&1; do
        echo -e "${YELLOW}⏳ Waiting for SuperTokens...${NC}"
        sleep 2
    done
    
    echo -e "${GREEN}✅ SuperTokens is ready!${NC}"
    
    # Display database information
    echo ""
    echo -e "${BLUE}📊 Database Information:${NC}"
    echo "========================"
    echo "SuperTokens Database:"
    echo "  - Host: localhost:5432"
    echo "  - Database: supertokens"
    echo "  - User: supertokens_user"
    echo ""
    echo "Flask Application Database:"
    echo "  - Host: localhost:5432"
    echo "  - Database: clarity_ai"
    echo "  - User: clarity_user"
    echo ""
    echo "SuperTokens Core:"
    echo "  - URL: http://localhost:3567"
    echo ""
    
    # Test connections
    test_connections
    
    echo ""
    echo -e "${GREEN}🎉 Database setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Update your backend/.env file with the database credentials"
    echo "2. Run your Flask application"
    echo "3. Run database migrations if needed"
    echo ""
    echo "To stop the services: $0 stop"
    echo "To view logs: $0 logs"
}

# Start services
start_services() {
    check_docker
    echo -e "${BLUE}📦 Starting database services...${NC}"
    docker compose up -d
    echo -e "${GREEN}✅ Services started${NC}"
}

# Stop services
stop_services() {
    echo -e "${BLUE}🛑 Stopping database services...${NC}"
    docker compose down
    echo -e "${GREEN}✅ Services stopped${NC}"
}

# Connect to Flask app database
connect_app() {
    check_container
    echo -e "${BLUE}🔗 Connecting to Flask app database...${NC}"
    docker exec -it $DB_CONTAINER psql -U $APP_USER -d $APP_DB
}

# Connect to SuperTokens database
connect_st() {
    check_container
    echo -e "${BLUE}🔗 Connecting to SuperTokens database...${NC}"
    docker exec -it $DB_CONTAINER psql -U $SUPERTOKENS_USER -d $SUPERTOKENS_DB
}

# List all databases
list_dbs() {
    check_container
    echo -e "${BLUE}📊 Listing all databases...${NC}"
    docker exec $DB_CONTAINER psql -U $SUPERTOKENS_USER -c "\l"
}

# Test database connections
test_connections() {
    check_container
    echo -e "${BLUE}🔍 Testing database connections...${NC}"
    
    # Test SuperTokens database
    if docker exec $DB_CONTAINER psql -U $SUPERTOKENS_USER -d $SUPERTOKENS_DB -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ SuperTokens database connection: OK${NC}"
    else
        echo -e "${RED}❌ SuperTokens database connection: FAILED${NC}"
    fi
    
    # Test Flask app database
    if docker exec $DB_CONTAINER psql -U $APP_USER -d $APP_DB -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Flask app database connection: OK${NC}"
    else
        echo -e "${RED}❌ Flask app database connection: FAILED${NC}"
    fi
}

# Backup Flask app database
backup_app() {
    check_container
    BACKUP_FILE="clarity_ai_backup_$(date +%Y%m%d_%H%M%S).sql"
    echo -e "${BLUE}💾 Creating backup: $BACKUP_FILE${NC}"
    docker exec $DB_CONTAINER pg_dump -U $APP_USER $APP_DB > $BACKUP_FILE
    echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"
}

# Restore Flask app database
restore_app() {
    check_container
    if [ -z "$2" ]; then
        echo -e "${RED}❌ Please specify backup file: $0 restore-app <backup_file>${NC}"
        exit 1
    fi
    
    BACKUP_FILE="$2"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}❌ Backup file not found: $BACKUP_FILE${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}🔄 Restoring database from: $BACKUP_FILE${NC}"
    echo -e "${YELLOW}⚠️  This will overwrite the current database. Continue? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        docker exec -i $DB_CONTAINER psql -U $APP_USER -d $APP_DB < $BACKUP_FILE
        echo -e "${GREEN}✅ Database restored successfully${NC}"
    else
        echo -e "${RED}❌ Restore cancelled${NC}"
    fi
}

# Reset Flask app database
reset_app() {
    check_container
    echo -e "${RED}⚠️  WARNING: This will delete ALL data in the Flask app database!${NC}"
    echo -e "${YELLOW}Are you sure you want to continue? (y/N)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🗑️  Dropping and recreating database...${NC}"
        docker exec $DB_CONTAINER psql -U $SUPERTOKENS_USER -c "DROP DATABASE IF EXISTS $APP_DB;"
        docker exec $DB_CONTAINER psql -U $SUPERTOKENS_USER -c "CREATE DATABASE $APP_DB;"
        docker exec $DB_CONTAINER psql -U $SUPERTOKENS_USER -c "GRANT ALL PRIVILEGES ON DATABASE $APP_DB TO $APP_USER;"
        echo -e "${GREEN}✅ Database reset complete${NC}"
    else
        echo -e "${RED}❌ Reset cancelled${NC}"
    fi
}

# Show PostgreSQL logs
show_logs() {
    echo -e "${BLUE}📋 PostgreSQL logs:${NC}"
    docker compose logs postgresql
}

# Show database status
show_status() {
    check_container
    echo -e "${BLUE}📊 Database Status:${NC}"
    echo "=================="
    
    # Container status
    echo "Container Status:"
    docker ps --filter name=$DB_CONTAINER --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "Database Connections:"
    
    # Test SuperTokens database
    if docker exec $DB_CONTAINER psql -U $SUPERTOKENS_USER -d $SUPERTOKENS_DB -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ SuperTokens database: Connected${NC}"
    else
        echo -e "${RED}❌ SuperTokens database: Connection failed${NC}"
    fi
    
    # Test Flask app database
    if docker exec $DB_CONTAINER psql -U $APP_USER -d $APP_DB -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Flask app database: Connected${NC}"
    else
        echo -e "${RED}❌ Flask app database: Connection failed${NC}"
    fi
    
    echo ""
    echo "Database Sizes:"
    docker exec $DB_CONTAINER psql -U $SUPERTOKENS_USER -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) as size FROM pg_database WHERE datname IN ('supertokens', 'clarity_ai');"
}

# Main script logic
case "$1" in
    "setup")
        setup_database
        ;;
    "start")
        start_services
        ;;
    "stop")
        stop_services
        ;;
    "connect-app")
        connect_app
        ;;
    "connect-st")
        connect_st
        ;;
    "list-dbs")
        list_dbs
        ;;
    "backup-app")
        backup_app
        ;;
    "restore-app")
        restore_app "$@"
        ;;
    "reset-app")
        reset_app
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "help"|"")
        show_usage
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac