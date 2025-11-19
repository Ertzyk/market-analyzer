from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Połączenie z NOWYM kontenerem:
#   docker run --name market-pg -e POSTGRES_PASSWORD=postgres -p 5433:5432 -d postgres
#   user:     postgres
#   password: postgres
#   host:     localhost
#   port:     5433 (na hoście)
#   db:       postgres
DATABASE_URL = "postgresql+pg8000://postgres:postgres@localhost:5433/postgres"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency dla FastAPI – daje sesję DB i zamyka po requestcie."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()