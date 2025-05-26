import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings

class PostgresDB:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=settings.postgres_client_url,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            cursor_factory=RealDictCursor
        )
        self.cur = self.conn.cursor()

    def __enter__(self):
        return self  

    def __exit__(self, exc_type, exc_value, traceback):
        self.cur.close()
        self.conn.close()


    def execute(self, query, params=None, fetch_one=False, fetch_all=False, commit=False):
        try:
            self.cur.execute(query, params or ())
            if commit:
                self.conn.commit()
            if fetch_one:
                return self.cur.fetchone()
            if fetch_all:
                return self.cur.fetchall()
        except Exception as e:
            print(f"❌ Query error: {e}")
            self.conn.rollback()
            return None

    def insert(self, table, data):
        keys = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({keys}) VALUES ({values}) RETURNING *"
        return self.execute(query, tuple(data.values()), fetch_one=True, commit=True)


    def select(self, table, conditions=None):
        query = f"SELECT * FROM {table}"
        params = []
        if conditions:
            filters = " AND ".join(f"{k} = %s" for k in conditions.keys())
            query += f" WHERE {filters}"
            params = list(conditions.values())
        return self.execute(query, params, fetch_all=True)

    def update(self, table, data, conditions):
        set_clause = ", ".join(f"{k} = %s" for k in data.keys())
        where_clause = " AND ".join(f"{k} = %s" for k in conditions.keys())
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause} RETURNING *"
        params = list(data.values()) + list(conditions.values())
        return self.execute(query, params, fetch_one=True, commit=True)

    def close(self):
        self.cur.close()
        self.conn.close()