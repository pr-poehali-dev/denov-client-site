"""
Аутентификация DenoV Client: регистрация, вход, профиль, аватар, телеграм, смена пароля, выход.
action: register | login | profile | update_avatar | update_telegram | change_password | logout
"""

import json
import os
import hashlib
import secrets
import base64
import psycopg2
import boto3
from datetime import datetime, timezone

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Session-Token',
}


def get_conn():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def get_s3():
    return boto3.client(
        's3',
        endpoint_url='https://bucket.poehali.dev',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    )


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


def get_user_by_token(token: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT u.uid, u.login, u.registered_at, u.last_login_at,
                  u.player_id, u.avatar_url, u.telegram, u.password_hash
           FROM denov_sessions s
           JOIN denov_users u ON u.uid = s.uid
           WHERE s.token = %s""",
        (token,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


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
                "INSERT INTO denov_users (login, password_hash) VALUES (%s, %s) RETURNING uid, login, registered_at, player_id",
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

        return ok({
            'token': new_token,
            'uid': uid,
            'player_id': row[3],
            'login': row[1],
            'registered_at': str(row[2]),
            'avatar_url': None,
            'telegram': None,
        })

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
            "SELECT uid, login, registered_at, player_id, avatar_url, telegram FROM denov_users WHERE login=%s AND password_hash=%s",
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
            'player_id': row[3],
            'login': row[1],
            'registered_at': str(row[2]),
            'last_login_at': str(now),
            'avatar_url': row[4],
            'telegram': row[5],
        })

    # PROFILE
    if action == 'profile':
        if not token:
            return err(401, 'Не авторизован')
        row = get_user_by_token(token)
        if not row:
            return err(401, 'Сессия не найдена')
        return ok({
            'uid': str(row[0]),
            'login': row[1],
            'registered_at': str(row[2]),
            'last_login_at': str(row[3]) if row[3] else None,
            'player_id': row[4],
            'avatar_url': row[5],
            'telegram': row[6],
        })

    # UPDATE AVATAR
    if action == 'update_avatar':
        if not token:
            return err(401, 'Не авторизован')
        row = get_user_by_token(token)
        if not row:
            return err(401, 'Сессия не найдена')

        image_b64 = body.get('image_b64', '')
        content_type = body.get('content_type', 'image/jpeg')
        if not image_b64:
            return err(400, 'Нет изображения')

        image_data = base64.b64decode(image_b64)
        if len(image_data) > 2 * 1024 * 1024:
            return err(400, 'Файл слишком большой (макс. 2MB)')

        uid = str(row[0])
        ext = 'png' if 'png' in content_type else 'jpg'
        key = f'denov/avatars/{uid}.{ext}'

        s3 = get_s3()
        s3.put_object(Bucket='files', Key=key, Body=image_data, ContentType=content_type)
        cdn_url = f"https://cdn.poehali.dev/projects/{os.environ['AWS_ACCESS_KEY_ID']}/bucket/{key}"

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE denov_users SET avatar_url=%s WHERE uid=%s", (cdn_url, uid))
        conn.commit()
        cur.close()
        conn.close()

        return ok({'avatar_url': cdn_url})

    # UPDATE TELEGRAM
    if action == 'update_telegram':
        if not token:
            return err(401, 'Не авторизован')
        row = get_user_by_token(token)
        if not row:
            return err(401, 'Сессия не найдена')

        tg = (body.get('telegram') or '').strip().lstrip('@')
        uid = str(row[0])

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE denov_users SET telegram=%s WHERE uid=%s", (tg or None, uid))
        conn.commit()
        cur.close()
        conn.close()

        return ok({'telegram': tg or None})

    # CHANGE PASSWORD
    if action == 'change_password':
        if not token:
            return err(401, 'Не авторизован')
        row = get_user_by_token(token)
        if not row:
            return err(401, 'Сессия не найдена')

        current_pw = body.get('current_password') or ''
        new_pw = body.get('new_password') or ''

        if not current_pw or not new_pw:
            return err(400, 'Заполните все поля')
        if len(new_pw) < 6:
            return err(400, 'Новый пароль минимум 6 символов')

        stored_hash = row[7]
        if hash_password(current_pw) != stored_hash:
            return err(401, 'Неверный текущий пароль')

        uid = str(row[0])
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE denov_users SET password_hash=%s WHERE uid=%s", (hash_password(new_pw), uid))
        conn.commit()
        cur.close()
        conn.close()

        return ok({'ok': True})

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
