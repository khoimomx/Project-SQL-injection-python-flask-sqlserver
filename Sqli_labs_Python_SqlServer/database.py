"""Provision the dedicated training database and isolate lesson connections."""

import os
import re
from contextlib import closing, contextmanager
from pathlib import Path

import pyodbc

# No privileged or impersonated session is returned to an ODBC pool.
pyodbc.pooling = False

DATABASE = "SQLiLabs_Flask_Training"
OWNER_MARK = "sqli-labs-flask.local"
SCHEMA_VERSION = "1"
SQL_DIR = Path(__file__).parent / "sql"


class DatabaseUnavailable(RuntimeError):
    pass


def _odbc_value(value):
    return "{" + value.replace("}", "}}") + "}"


def connect(database, *, autocommit=False):
    driver = os.environ.get("LAB_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.environ.get("LAB_SQL_SERVER", "localhost")
    options = {
        "DRIVER": driver,
        "SERVER": server,
        "DATABASE": database,
        "Encrypt": "yes",
        "TrustServerCertificate": "yes",  # local training instance
        "APP": "SQLi Labs Flask",
    }
    login = os.environ.get("LAB_SQL_USER")
    if login:
        options.update(UID=login, PWD=os.environ["LAB_SQL_PASSWORD"])
    else:
        options["Trusted_Connection"] = "yes"
    dsn = ";".join(f"{key}={_odbc_value(value)}" for key, value in options.items())
    return pyodbc.connect(dsn, timeout=5, autocommit=autocommit)


def _property(cursor, name):
    row = cursor.execute(
        "SELECT CONVERT(varchar(100), value) FROM sys.extended_properties "
        "WHERE class = 0 AND name = ?", name,
    ).fetchone()
    return row[0] if row else None


def _run_sql(cursor, filename):
    sql = (SQL_DIR / filename).read_text(encoding="utf-8")
    for batch in re.split(r"(?im)^\s*GO\s*$", sql):
        if batch.strip():
            cursor.execute(batch)
            while cursor.nextset():
                pass


def initialize(*, reset=False):
    """Serialize setup, and refuse to adopt an unmarked existing database."""
    with closing(connect("master", autocommit=True)) as master:
        cursor = master.cursor()
        lock = cursor.execute(
            "SET NOCOUNT ON; DECLARE @r int; EXEC @r = sys.sp_getapplock "
            "@Resource=N'SQLiLabs_Flask_Training.setup', @LockMode='Exclusive', "
            "@LockOwner='Session', @LockTimeout=10000; SELECT @r"
        ).fetchval()
        if lock < 0:
            raise RuntimeError("Một tiến trình khác đang khởi tạo lab. Hãy thử lại.")
        exists = cursor.execute("SELECT DB_ID(?)", DATABASE).fetchval() is not None
        if not exists:
            if reset:
                raise RuntimeError("Chưa có database lab. Hãy chạy python app.py init.")
            cursor.execute(f"CREATE DATABASE [{DATABASE}]")
        with closing(connect(DATABASE)) as db:
            cur = db.cursor()
            if not exists:
                cur.execute(
                    "EXEC sys.sp_addextendedproperty @name=N'LabOwner', @value=?",
                    OWNER_MARK,
                )
                db.commit()
            if _property(cur, "LabOwner") != OWNER_MARK:
                raise RuntimeError(f"Database {DATABASE} đã tồn tại và không thuộc lab. Đã dừng.")
            version = _property(cur, "LabSchema")
            if version is None:
                _run_sql(cur, "schema.sql")
                _run_sql(cur, "seed.sql")
                cur.execute("EXEC sys.sp_addextendedproperty @name=N'LabSchema', @value=?",
                            SCHEMA_VERSION)
            elif version != SCHEMA_VERSION:
                raise RuntimeError(f"Phiên bản schema chưa được hỗ trợ: {version}")
            elif reset:
                _run_sql(cur, "seed.sql")
            db.commit()


@contextmanager
def training_connection(scope):
    try:
        db = connect(DATABASE, autocommit=True)
    except (pyodbc.Error, KeyError) as exc:
        raise DatabaseUnavailable("Không kết nối được database lab.") from exc
    with closing(db):
        try:
            db.timeout = 7
            cur = db.cursor()
            cur.execute("EXECUTE AS USER = 'lab_student' WITH NO REVERT")
            cur.execute("SET NOCOUNT ON; SET LOCK_TIMEOUT 4500; SET XACT_ABORT ON")
            cur.execute("EXEC sys.sp_set_session_context @key=N'lab_scope', "
                        "@value=?, @read_only=1", scope)
            cur.close()
            db.autocommit = False
        except pyodbc.Error as exc:
            raise DatabaseUnavailable("Chưa mở được phiên lab giới hạn quyền.") from exc
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
