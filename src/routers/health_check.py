from fastapi import APIRouter, HTTPException
from database.postgresdb import PostgresDB
from config import settings

router = APIRouter(prefix='/health_check', tags=["ping"])


@router.get("/")
def health_check():
    return {
        "status":"ok"
    }

@router.get("/postgres")
def check_postgres():
    try:
        with PostgresDB() as db:
            db.cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row['table_name'] for row in db.cur.fetchall()]
            return {
                "status": "connected",
                "host": settings.postgres_client_url,
                "port": settings.postgres_port,
                "user": settings.postgres_user,
                "database": "postgres",
                "tables": tables
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Postgres connection failed: {e}")