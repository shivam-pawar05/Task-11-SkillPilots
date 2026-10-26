import logging
import re
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError

from config import MASTER, REPLICA

# Create the logs directory automatically.
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "query_audit.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def create_db_engine(config):
    """Create a SQLAlchemy engine for a MySQL server."""
    url = URL.create(
        drivername="mysql+pymysql",
        username=config["username"],
        password=config["password"],
        host=config["host"],
        port=config["port"],
        database=config["database"],
        query={"charset": "utf8mb4"},
    )

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


# Maintain two separate database engines.
master_engine = create_db_engine(MASTER)
replica_engine = create_db_engine(REPLICA)


def is_read_query(sql):
    """Return True only for ordinary SELECT queries."""

    query = sql.strip()

    # Remove leading SQL comments.
    query = re.sub(
        r"(?s)^(?:\s*(?:--[^\n]*\n|#[^\n]*\n|/\*.*?\*/))*",
        "",
        query,
    ).lstrip()

    # Only SELECT statements are candidates for replica routing.
    if not re.match(r"(?i)^SELECT\b", query):
        return False

    # Locking reads must go to the master.
    if re.search(
        r"(?i)\bFOR\s+UPDATE\b|\bLOCK\s+IN\s+SHARE\s+MODE\b",
        query,
    ):
        return False

    return True


def execute_query(sql, params=None):
    """Route and execute a query with optional bound parameters."""

    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL query cannot be empty.")

    read_query = is_read_query(sql)

    if read_query:
        engine = replica_engine
        destination = "REPLICA"
    else:
        engine = master_engine
        destination = "MASTER"

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(sql),
                params or {},
            )

            if result.returns_rows:
                rows = [
                    dict(row._mapping)
                    for row in result
                ]

                logging.info(
                    "Destination=%s | Rows=%s | Query=%s",
                    destination,
                    len(rows),
                    sql.replace("\n", " ")[:500],
                )

                return rows

            affected_rows = result.rowcount
            connection.commit()

            logging.info(
                "Destination=%s | Affected rows=%s | Query=%s",
                destination,
                affected_rows,
                sql.replace("\n", " ")[:500],
            )

            return affected_rows

    except SQLAlchemyError:
        logging.exception(
            "Query failed | Destination=%s | Query=%s",
            destination,
            sql.replace("\n", " ")[:500],
        )
        raise


if __name__ == "__main__":
    try:
        # Test 1: SELECT goes to the replica.
        rows = execute_query(
            "SELECT id, name, price FROM products ORDER BY id"
        )
        print("SELECT result:", rows)

        # Test 2: INSERT goes to the master.
        inserted = execute_query(
            """
            INSERT INTO products (name, price)
            VALUES (:name, :price)
            """,
            {"name": "Demo Product", "price": 99.50},
        )
        print("Rows inserted:", inserted)

        # Test 3: UPDATE goes to the master.
        updated = execute_query(
            """
            UPDATE products
            SET price = :price
            WHERE name = :name
            """,
            {"price": 109.50, "name": "Demo Product"},
        )
        print("Rows updated:", updated)

    finally:
        master_engine.dispose()
        replica_engine.dispose()