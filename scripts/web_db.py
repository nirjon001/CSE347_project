#!/usr/bin/env python3
"""
web_db.py -- manage the FREE web copy's database (Aiven MySQL over TLS).

Why Python instead of XAMPP's mysql.exe?
  XAMPP ships a MariaDB client that cannot authenticate to MySQL 8 hosts
  (Aiven uses the caching_sha2_password plugin). The app already depends on
  mysql-connector-python, which handles MySQL 8 + TLS natively, so this tool
  uses that same library.

WEB vs LOCAL terminology:
  * WEB  = the deployed copy's database (Aiven MySQL 8 over TLS). Env keys
           DB_* (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_SSL_CA).
  * LOCAL = the XAMPP MariaDB database on this PC. Env keys LOCAL_DB_* plus
           MYSQLDUMP_EXE / MYSQL_EXE (XAMPP binaries), which cannot talk to
           MySQL 8, so all WEB-side access here uses mysql-connector-python.

Commands:
  init        One-time import: create the database if needed, then import
              hostel_management_schema.sql + seed_data.sql.      (WEB side)
  drop        DROP the web database.                             (WEB side)
  push        Dump the LOCAL XAMPP database (mysqldump) and import it into
              the web database. (LOCAL -> WEB)
  pull        Dump the web database and import it into the local XAMPP DB.
                                                                  (WEB -> LOCAL)

Configuration lives in scripts/.web-db.env (git-ignored). See
scripts/.web-db.env.example for the template.
"""

import subprocess
import sys
import argparse
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent


def load_env(path: Path) -> dict:
    cfg = {}
    if not path.is_file():
        print(f"ERROR: {path} not found. Copy .web-db.env.example to .web-db.env and fill it in.")
        sys.exit(1)
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            cfg[key.strip()] = value
    return cfg


def resolve_ca(value: str):
    if not value:
        return None
    for candidate in (Path(value), ROOT / value, SCRIPTS / value):
        if candidate.is_file():
            return str(candidate)
    print(f"ERROR: CA certificate file not found: {value}")
    sys.exit(1)


def connect(cfg, database=None):
    import mysql.connector

    kwargs = {
        "host": cfg.get("DB_HOST", ""),
        "port": int(cfg.get("DB_PORT", "3306")),
        "user": cfg.get("DB_USER", ""),
        "password": cfg.get("DB_PASSWORD", ""),
        "charset": "utf8mb4",
    }
    if not kwargs["host"] or not kwargs["user"]:
        print("ERROR: missing DB_HOST / DB_USER in .web-db.env")
        sys.exit(1)
    if database:
        kwargs["database"] = database
    ssl_ca = resolve_ca(cfg.get("DB_SSL_CA", ""))
    if ssl_ca:
        kwargs.update(ssl_ca=ssl_ca, ssl_verify_cert=True, ssl_verify_identity=True)
    return mysql.connector.connect(**kwargs)


def split_sql(sql_text: str):
    """Split a .sql file into executable statements, honoring MySQL's
    DELIMITER directive, -- / # line comments, /* */ block comments, and
    '...' / "..." / `...` quoting (with backslash escaping)."""
    statements = []
    cur = []
    delim = ";"
    i, n = 0, len(sql_text)
    in_line_c = in_block_c = esc = False
    quote = None
    at_line_start = True
    while i < n:
        ch = sql_text[i]
        nxt = sql_text[i + 1] if i + 1 < n else ""
        if in_line_c:
            cur.append(ch)
            if ch == "\n":
                in_line_c = False
                at_line_start = True
            i += 1
            continue
        if in_block_c:
            if ch == "*" and nxt == "/":
                cur.append("*/")
                i += 2
                in_block_c = False
            else:
                cur.append(ch)
                i += 1
            continue
        if quote:
            cur.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch == "-" and nxt == "-":
            in_line_c = True
            cur.append("--")
            i += 2
            continue
        if ch == "#":
            in_line_c = True
            cur.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "*":
            in_block_c = True
            cur.append("/*")
            i += 2
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            cur.append(ch)
            i += 1
            at_line_start = False
            continue
        if at_line_start and ch not in " \t\r\n":
            j = sql_text.find("\n", i)
            if j == -1:
                j = n
            line = sql_text[i:j].strip()
            if line.upper().startswith("DELIMITER"):
                parts = line.split()
                if len(parts) >= 2:
                    delim = parts[1]
                    cur = []
                    i = j
                    continue
        if sql_text.startswith(delim, i):
            stmt = "".join(cur).strip()
            if stmt:
                statements.append(stmt)
            cur = []
            i += len(delim)
            at_line_start = False
            continue
        cur.append(ch)
        if ch in "\r\n":
            at_line_start = True
        elif ch not in " \t":
            at_line_start = False
        i += 1
    if "".join(cur).strip():
        statements.append("".join(cur).strip())
    return statements


def execute_sql(conn, statements, label):
    executed = []
    cur = conn.cursor()
    for stmt in statements:
        if not _sig(stmt):
            continue
        cur.execute(stmt)
        executed.append(stmt)
    cur.close()
    print(f"  {label}: executed {len(executed)} statement(s)")
    return executed


def _sig(stmt):
    """Lowercased start of a statement, ignoring leading comment-only lines."""
    lines = stmt.splitlines()
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if not s or s.startswith(("--", "#", "/*")):
            continue
        return " ".join("\n".join(lines[i:]).strip().split()).lower()
    return ""


def strip_create_use(statements):
    kept = []
    for stmt in statements:
        low = _sig(stmt)
        if low.startswith("create database") or low.startswith("use "):
            continue
        kept.append(stmt)
    return kept


def verify_counts(conn):
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [r[0] for r in cur.fetchall()]
    print(f"  tables in web DB ({len(tables)}):")
    for t in sorted(tables):
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        print(f"    {t}: {cur.fetchone()[0]}")
    cur.close()


def cmd_init(cfg):
    db = cfg.get("DB_NAME", "hostel_management")
    import mysql.connector

    conn = connect(cfg)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4")
    cur.close()
    conn.close()
    print(f"Database `{db}` ready on {cfg['DB_HOST']}")

    conn = connect(cfg, database=db)
    conn.autocommit = True

    schema = (ROOT / "hostel_management_schema.sql").read_text(encoding="utf-8")
    seed = (ROOT / "seed_data.sql").read_text(encoding="utf-8")
    stmts_schema = split_sql(schema)
    stmts_seed = split_sql(seed)
    if cfg.get("DB_STRIP_USING", "1") == "1":
        print("DB_STRIP_USING=1: dropping CREATE DATABASE / USE statements...")
        stmts_schema = strip_create_use(stmts_schema)
        stmts_seed = strip_create_use(stmts_seed)

    try:
        execute_sql(conn, stmts_schema, "schema")
        execute_sql(conn, stmts_seed, "seed data")
        verify_counts(conn)
    except mysql.connector.Error as exc:
        print(f"FAILED during import: {exc}")
        print("  If tables already exist, drop the database first (Aiven console, or web_db.py drop) and re-run init.")
        sys.exit(1)
    finally:
        conn.close()

    print("SUCCESS: web database is populated. Logins: manager/admin123, staff1-3/staff123, student1-5/student123")


def cmd_drop(cfg):
    db = cfg.get("DB_NAME", "hostel_management")
    conn = connect(cfg)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"DROP DATABASE IF EXISTS `{db}`")
    cur.close()
    conn.close()
    print(f"Dropped database `{db}`.")


def dump_local(cfg):
    mysqldump = cfg.get("MYSQLDUMP_EXE", r"C:\xampp\mysql\bin\mysqldump.exe")
    if not Path(mysqldump).is_file():
        print(f"ERROR: mysqldump not found at {mysqldump}")
        sys.exit(1)
    cmd = [
        mysqldump,
        "-h", cfg.get("LOCAL_DB_HOST", "127.0.0.1"),
        "-P", cfg.get("LOCAL_DB_PORT", "3306"),
        "-u", cfg.get("LOCAL_DB_USER", "root"),
        f"-p{cfg.get('LOCAL_DB_PASSWORD', '')}",
        "--single-transaction", "--skip-lock-tables", "--default-character-set=utf8mb4",
        cfg.get("LOCAL_DB_NAME", "hostel_management"),
    ]
    print("  dumping local DB...")
    return subprocess.run(cmd, capture_output=True, text=True)


def import_to_web(cfg, sql_text):
    import mysql.connector

    db = cfg.get("DB_NAME", "hostel_management")
    conn = connect(cfg, database=db)
    conn.autocommit = True
    stmts = split_sql(sql_text)
    try:
        execute_sql(conn, stmts, "web import")
    except mysql.connector.Error as exc:
        print(f"FAILED during import: {exc}")
        sys.exit(1)
    finally:
        conn.close()


def cmd_push(cfg):
    res = dump_local(cfg)
    if res.returncode != 0:
        print("FAILED dumping local DB:")
        print(res.stderr)
        sys.exit(1)
    import_to_web(cfg, res.stdout)
    print(f"SUCCESS: local {cfg.get('LOCAL_DB_NAME', 'hostel_management')} pushed to web {cfg.get('DB_NAME', 'hostel_management')}")


def mysql_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, bytes):
        return "0x" + v.hex()
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    if isinstance(v, datetime):
        return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"
    if isinstance(v, (date, time)):
        return "'" + v.isoformat() + "'"
    if isinstance(v, str):
        return "'" + v.replace("\\", "\\\\").replace("'", "\\'").replace("\x00", "") + "'"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "\\'") + "'"


def dump_web(cfg):
    import mysql.connector

    db = cfg.get("DB_NAME", "hostel_management")
    conn = connect(cfg, database=db)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [r[0] for r in cur.fetchall()]
    lines = []
    lines.append("SET NAMES utf8mb4;")
    for t in sorted(tables):
        cur.execute(f"SHOW CREATE TABLE `{t}`")
        lines.append("-- -----")
        lines.append(f"DROP TABLE IF EXISTS `{t}`;")
        lines.append(cur.fetchone()[1] + ";")
        cur.execute(f"SELECT * FROM `{t}`")
        cols = [d[0] for d in cur.description]
        for row in cur.fetchall():
            vals = ", ".join(mysql_value(v) for v in row)
            lines.append(f"INSERT INTO `{t}` (`{'`, `'.join(cols)}`) VALUES ({vals});")
    cur.execute("SHOW TRIGGERS")
    triggers = cur.fetchall()
    for t_row in triggers:
        trig = t_row[0]
        cur.execute(f"SHOW CREATE TRIGGER `{trig}`")
        create_stmt = cur.fetchone()[2]
        lines.append("DROP TRIGGER IF EXISTS `%s`;" % trig)
        lines.append("DELIMITER //")
        lines.append(create_stmt)
        lines.append("//")
        lines.append("DELIMITER ;")
    cur.close()
    conn.close()
    return "\n".join(lines) + "\n"


def apply_to_local(cfg, sql_text):
    mysql = cfg.get("MYSQL_EXE", r"C:\xampp\mysql\bin\mysql.exe")
    if not Path(mysql).is_file():
        print(f"ERROR: mysql client not found at {mysql}")
        sys.exit(1)
    cmd = [
        mysql,
        "-h", cfg.get("LOCAL_DB_HOST", "127.0.0.1"),
        "-P", cfg.get("LOCAL_DB_PORT", "3306"),
        "-u", cfg.get("LOCAL_DB_USER", "root"),
        f"-p{cfg.get('LOCAL_DB_PASSWORD', '')}",
        "--default-character-set=utf8mb4",
        cfg.get("LOCAL_DB_NAME", "hostel_management"),
    ]
    res = subprocess.run(cmd, input=sql_text, capture_output=True, text=True)
    if res.returncode != 0:
        print("FAILED importing into local DB:")
        print(res.stderr)
        sys.exit(1)
    print("  local import OK")


def cmd_pull(cfg):
    print("  dumping web DB...")
    dump = dump_web(cfg)
    apply_to_local(cfg, dump)
    print(f"SUCCESS: web {cfg.get('DB_NAME', 'hostel_management')} pulled to local {cfg.get('LOCAL_DB_NAME', 'hostel_management')}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "drop", "push", "pull"])
    parser.add_argument("--env", default=str(SCRIPTS / ".web-db.env"))
    args = parser.parse_args()

    cfg = load_env(Path(args.env))
    if args.command == "init":
        cmd_init(cfg)
    elif args.command == "drop":
        cmd_drop(cfg)
    elif args.command == "push":
        cmd_push(cfg)
    elif args.command == "pull":
        cmd_pull(cfg)


if __name__ == "__main__":
    main()
