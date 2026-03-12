"""
Аутентификация DenoV Client: регистрация, вход, профиль, выход.
action: register | login | profile | logout
"""

import json
import os
import hashlib
import secrets
import psycopg2
from datetime import datetime, timezone

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Session-Token',
}


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def ok(data: dict) -> dict:
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
        'body': json.dumps(data, ensure_ascii=False, default=str),
    }


def err(status: int, message: str) -> dict:
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json', **CORS_HEADERS},
        'body': json.dumps({'error': message}, ensure_ascii=False),
    }


def handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    body = {}
    if event.get('body'):
        body = json.loads(event['body'])

    action = body.get('action', '')
    headers = event.get('headers') or {}
    token = headers.get('X-Session-Token', '')

    # REGISTER
    if action == 'register':
        login = (body.get('login') or '').strip()
        password = body.get('password') or ''

        if not login or not password:
            return err(400, 'Логин и пароль обязательны')
        if len(login) < 3:
            return err(400, 'Логин минимум 3 символа')
        if len(password) < 6:
            return err(400, 'Пароль минимум 6 символов')

        pw_hash = hash_password(password)
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO denov_users (login, password_hash) VALUES (%s, %s) RETURNING uid, login, registered_at",
                (login, pw_hash)
            )
            row = cur.fetchone()
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            cur.close()
            conn.close()
            return err(409, 'Логин уже занят')

        uid = str(row[0])
        new_token = secrets.token_hex(32)
        cur.execute("INSERT INTO denov_sessions (token, uid) VALUES (%s, %s)", (new_token, uid))
        conn.commit()
        cur.close()
        conn.close()

        return ok({'token': new_token, 'uid': uid, 'login': row[1], 'registered_at': str(row[2])})

    # LOGIN
    if action == 'login':
        login = (body.get('login') or '').strip()
        password = body.get('password') or ''

        if not login or not password:
            return err(400, 'Логин и пароль обязательны')

        pw_hash = hash_password(password)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT uid, login, registered_at FROM denov_users WHERE login=%s AND password_hash=%s",
            (login, pw_hash)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return err(401, 'Неверный логин или пароль')

        uid = str(row[0])
        now = datetime.now(timezone.utc)
        cur.execute("UPDATE denov_users SET last_login_at=%s WHERE uid=%s", (now, uid))
        new_token = secrets.token_hex(32)
        cur.execute("INSERT INTO denov_sessions (token, uid) VALUES (%s, %s)", (new_token, uid))
        conn.commit()
        cur.close()
        conn.close()

        return ok({
            'token': new_token,
            'uid': uid,
            'login': row[1],
            'registered_at': str(row[2]),
            'last_login_at': str(now),
        })

    # PROFILE
    if action == 'profile':
        if not token:
            return err(401, 'Не авторизован')

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """SELECT u.uid, u.login, u.registered_at, u.last_login_at
               FROM denov_sessions s
               JOIN denov_users u ON u.uid = s.uid
               WHERE s.token = %s""",
            (token,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return err(401, 'Сессия не найдена')

        return ok({
            'uid': str(row[0]),
            'login': row[1],
            'registered_at': str(row[2]),
            'last_login_at': str(row[3]) if row[3] else None,
        })

    # LOGOUT
    if action == 'logout':
        if token:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM denov_sessions WHERE token=%s", (token,))
            conn.commit()
            cur.close()
            conn.close()
        return ok({'ok': True})

    return err(400, 'Неизвестное действие')
