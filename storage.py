"""
storage.py - Persistencia local em SQLite para usuarios, squads e workspaces.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


def init_db(database_path: str) -> None:
    """Garante a existencia do banco, suas tabelas e migracoes simples."""
    db_file = Path(database_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_file) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS squads (
                name TEXT NOT NULL,
                owner_username TEXT,
                squad_data TEXT NOT NULL,
                workspace_data TEXT,
                PRIMARY KEY (owner_username, name)
            )
            """
        )
        _ensure_squads_schema(connection)
        connection.commit()


def _ensure_squads_schema(connection: sqlite3.Connection) -> None:
    table_info = connection.execute("PRAGMA table_info(squads)").fetchall()
    columns = {row[1] for row in table_info}
    pk_columns = [row[1] for row in sorted(table_info, key=lambda row: row[5]) if row[5] > 0]

    if "owner_username" in columns and pk_columns == ["owner_username", "name"]:
        return

    connection.execute("ALTER TABLE squads RENAME TO squads_legacy")
    connection.execute(
        """
        CREATE TABLE squads (
            name TEXT NOT NULL,
            owner_username TEXT,
            squad_data TEXT NOT NULL,
            workspace_data TEXT,
            PRIMARY KEY (owner_username, name)
        )
        """
    )

    legacy_columns = {row[1] for row in connection.execute("PRAGMA table_info(squads_legacy)").fetchall()}
    owner_expression = "owner_username" if "owner_username" in legacy_columns else "NULL"
    connection.execute(
        f"""
        INSERT INTO squads(name, owner_username, squad_data, workspace_data)
        SELECT name, {owner_expression}, squad_data, workspace_data
        FROM squads_legacy
        """
    )
    connection.execute("DROP TABLE squads_legacy")


def create_user(database_path: str, username: str, password: str) -> int:
    """Cria um usuario e retorna seu identificador."""
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO users(username, password_hash)
            VALUES (?, ?)
            """,
            (username, generate_password_hash(password)),
        )
        connection.commit()
        return int(cursor.lastrowid)


def get_user_by_username(database_path: str, username: str) -> dict | None:
    """Retorna os dados do usuario pelo nome."""
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if not row:
        return None
    return {"id": row[0], "username": row[1], "password_hash": row[2]}


def authenticate_user(database_path: str, username: str, password: str) -> dict | None:
    """Valida credenciais e retorna os dados do usuario autenticado."""
    user = get_user_by_username(database_path, username)
    if not user:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return {"id": user["id"], "username": user["username"]}


def load_all_squads(database_path: str, owner_username: str | None) -> dict:
    """Retorna todas as squads persistidas do usuario informado."""
    if not owner_username:
        return {}

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT name, squad_data
            FROM squads
            WHERE owner_username = ?
            ORDER BY name
            """,
            (owner_username,),
        ).fetchall()

    squads_data = {}
    for name, squad_json in rows:
        squads_data[name] = json.loads(squad_json)
    return squads_data


def load_all_workspaces(database_path: str, owner_username: str | None) -> dict:
    """Retorna todos os workspaces persistidos do usuario informado."""
    if not owner_username:
        return {}

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT name, workspace_data
            FROM squads
            WHERE owner_username = ? AND workspace_data IS NOT NULL
            """,
            (owner_username,),
        ).fetchall()

    workspaces = {}
    for name, workspace_json in rows:
        workspaces[name] = json.loads(workspace_json)
    return workspaces


def replace_all_squads(database_path: str, owner_username: str, squads_data: dict) -> None:
    """Substitui integralmente o conjunto de squads salvo do usuario informado."""
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "DELETE FROM squads WHERE owner_username = ?",
            (owner_username,),
        )
        connection.executemany(
            """
            INSERT INTO squads(name, owner_username, squad_data, workspace_data)
            VALUES (?, ?, ?, NULL)
            """,
            [
                (name, owner_username, json.dumps(squad_info))
                for name, squad_info in squads_data.items()
            ],
        )
        connection.commit()


def upsert_squad(
    database_path: str,
    owner_username: str,
    squad_name: str,
    squad_info: dict,
) -> None:
    """Cria ou atualiza os dados base de uma squad sem perder workspace."""
    with sqlite3.connect(database_path) as connection:
        existing = connection.execute(
            """
            SELECT workspace_data
            FROM squads
            WHERE owner_username = ? AND name = ?
            """,
            (owner_username, squad_name),
        ).fetchone()
        workspace_json = existing[0] if existing else None
        connection.execute(
            """
            INSERT OR REPLACE INTO squads(name, owner_username, squad_data, workspace_data)
            VALUES (?, ?, ?, ?)
            """,
            (squad_name, owner_username, json.dumps(squad_info), workspace_json),
        )
        connection.commit()


def save_workspace(
    database_path: str,
    owner_username: str,
    squad_name: str,
    workspace: dict,
) -> None:
    """Persiste o workspace da squad informada."""
    with sqlite3.connect(database_path) as connection:
        squad_exists = connection.execute(
            """
            SELECT 1
            FROM squads
            WHERE owner_username = ? AND name = ?
            """,
            (owner_username, squad_name),
        ).fetchone()
        if not squad_exists:
            connection.execute(
                """
                INSERT INTO squads(name, owner_username, squad_data, workspace_data)
                VALUES (?, ?, ?, ?)
                """,
                (
                    squad_name,
                    owner_username,
                    json.dumps({"members": [], "total_cost": 0}),
                    json.dumps(workspace),
                ),
            )
        else:
            connection.execute(
                """
                UPDATE squads
                SET workspace_data = ?
                WHERE owner_username = ? AND name = ?
                """,
                (json.dumps(workspace), owner_username, squad_name),
            )
        connection.commit()


def clear_all_data(database_path: str, owner_username: str) -> None:
    """Remove os dados persistidos do usuario informado."""
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "DELETE FROM squads WHERE owner_username = ?",
            (owner_username,),
        )
        connection.commit()


def delete_squad(database_path: str, owner_username: str, squad_name: str) -> bool:
    """Remove uma squad especifica do usuario informado."""
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM squads
            WHERE owner_username = ? AND name = ?
            """,
            (owner_username, squad_name),
        )
        connection.commit()
        return cursor.rowcount > 0
