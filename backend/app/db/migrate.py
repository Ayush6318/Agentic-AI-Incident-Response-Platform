from pathlib import Path
import psycopg
from app.config import settings


MIGRATIONS = Path(__file__).parent / "migrations"

def run():
    with psycopg.connect(settings.DATABASE_URL, autocommit=True) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                            name TEXT PRIMARY KEY,
                            applied_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
        done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
        for f in sorted(MIGRATIONS.glob("*.sql")):
            if f.name in done:
                continue
            with conn.transaction():                     
                conn.execute(f.read_text())
                conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (f.name,))
            print("applied", f.name)

if __name__ == "__main__":
    run()