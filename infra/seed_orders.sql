-- Seed realistic data into orders table for development/testing
-- Adjust columns to match your actual schema

-- Example minimal schema (uncomment if needed on a fresh DB)
-- CREATE TABLE IF NOT EXISTS users (
--   id SERIAL PRIMARY KEY,
--   username TEXT
-- );
-- CREATE TABLE IF NOT EXISTS orders (
--   id SERIAL PRIMARY KEY,
--   user_id INTEGER,
--   product_id INTEGER,
--   quantity INTEGER,
--   created_at TIMESTAMP DEFAULT NOW()
-- );

INSERT INTO orders(user_id, created_at)
SELECT (random()*1000)::int,
       NOW() - (interval '1 minute' * (50000 - id))
FROM generate_series(1, 50000) AS id;

VACUUM ANALYZE orders;


