#!/bin/bash

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default values
POSTGRES_SERVER=${POSTGRES_SERVER:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
POSTGRES_DB=${POSTGRES_DB:-payment_system}

echo "Initializing database: $POSTGRES_DB on $POSTGRES_SERVER:$POSTGRES_PORT"

# Check if database exists, if not create it
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -p $POSTGRES_PORT -U $POSTGRES_USER -tc "SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB'" | grep -q 1 || PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -p $POSTGRES_PORT -U $POSTGRES_USER -c "CREATE DATABASE $POSTGRES_DB"

# Run initialization script
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f sql/init.sql

echo "Database initialized successfully!"