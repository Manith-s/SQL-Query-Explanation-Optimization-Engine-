# Infrastructure

This directory contains infrastructure configuration and database setup files.

## Database Setup

### PostgreSQL (Primary Database)

The application is designed to work with PostgreSQL as the primary database. In Phase 2, we'll add:

- Database connection management
- Schema creation and migration
- Sample data seeding
- EXPLAIN plan analysis

### SQLite (Optional)

For development and demos, SQLite can be used as an alternative database.

## Files

- `seed.sql` - Database schema and sample data (placeholder for Phase 2)

## Usage

### Phase 0 (Current)
- No database setup required
- All endpoints return stub responses

### Phase 2 (Future)
1. Start PostgreSQL container: `docker-compose up db`
2. Run schema creation: `psql -h localhost -U postgres -d queryexpnopt -f infra/seed.sql`
3. Configure database connection in environment variables

## Environment Variables

```bash
# Database configuration (Phase 2+)
DB_URL=postgresql://user:pass@localhost:5432/queryexpnopt
DB_HOST=localhost
DB_PORT=5432
DB_NAME=queryexpnopt
DB_USER=postgres
DB_PASSWORD=password
```

## Docker Compose

The `docker-compose.yml` file in the root directory includes:

- PostgreSQL 16 database service
- API service (commented out for Phase 0)

To start just the database:
```bash
docker-compose up db
```
