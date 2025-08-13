from app.core.config import settings
import psycopg2

print("Loaded DB_URL from settings:", settings.DB_URL)

# Convert to psycopg2-friendly format and force IPv4
dsn = settings.DB_URL.replace("postgresql+psycopg2://", "postgresql://").replace("localhost", "127.0.0.1")
print("Using connection string:", dsn)

try:
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print("Connected successfully! PostgreSQL version:", version[0])
    cur.close()
    conn.close()
except Exception as e:
    print("Database connection failed:", e)
