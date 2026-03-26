from __future__ import annotations

import os
import secrets
import smtplib
import ssl
import bcrypt

from email.mime.text import MIMEText
from fastapi import FastAPI, Header, HTTPException
from sqlalchemy import text as sql

from .db import engine

app = FastAPI(title="Account API", version="2.1")

ADMIN_KEY = os.getenv("ACCOUNT_ADMIN_KEY", "admin-dev-key")

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER).strip()


@app.get("/health")
def health():
    return {"status": "ok", "service": "account_api"}


def _hash_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_key(raw_key: str, key_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_key.encode("utf-8"), key_hash.encode("utf-8"))
    except Exception:
        return False


def _send_account_email(
    to_email: str,
    full_name: str,
    employee_key: str,
    office_country: str,
    position: str,
) -> None:
    if not to_email:
        raise RuntimeError("Recipient email is empty")

    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and SMTP_FROM):
        raise RuntimeError("SMTP is not configured in account_api .env")

    subject = "Your PR Messenger account has been created"
    body = f"""Hello, {full_name}.

Your PR Messenger account has been created.

Your employee key:
{employee_key}

Do not share this key with anyone.

Office country: {office_country}
Position: {position}

If you did not expect this message, contact HR or your administrator.
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    context = ssl.create_default_context()

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())

    print(f"[EMAIL SENT] from={SMTP_FROM} to={to_email}")


def _get_user_by_key(x_employee_key: str | None):
    if not x_employee_key:
        raise HTTPException(status_code=401, detail="X-Employee-Key required")

    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT
                id, full_name, phone, email, office_country, position,
                employment_date, key_hash, is_active, role
            FROM dbo.employees
            WHERE is_active = 1
        """)).mappings().all()

    for r in rows:
        if _check_key(x_employee_key, r["key_hash"]):
            return r

    raise HTTPException(status_code=401, detail="Invalid employee key")


def _require_hr_or_admin(x_employee_key: str | None):
    user = _get_user_by_key(x_employee_key)
    role = str(user.get("role") or "employee").lower()
    if role not in ("admin", "hr"):
        raise HTTPException(status_code=403, detail="HR/Admin access required")
    return user


@app.post("/auth/verify")
def verify_key(x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    user = _get_user_by_key(x_employee_key)
    return {
        "id": int(user["id"]),
        "full_name": user["full_name"],
        "phone": user["phone"],
        "email": user["email"],
        "office_country": user["office_country"],
        "position": user["position"],
        "employment_date": str(user["employment_date"]),
        "role": user["role"],
    }


@app.get("/me")
def me(x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    return verify_key(x_employee_key)


@app.get("/employees")
def list_employees(x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    _require_hr_or_admin(x_employee_key)

    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT
                id, full_name, phone, email, office_country, position,
                employment_date, is_active, role, created_at
            FROM dbo.employees
            ORDER BY full_name ASC
        """)).mappings().all()

    return {"items": [dict(r) for r in rows]}


@app.get("/employees/{employee_id}")
def get_employee(employee_id: int, x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    _require_hr_or_admin(x_employee_key)

    with engine.connect() as conn:
        row = conn.execute(sql("""
            SELECT
                id, full_name, phone, email, office_country, position,
                employment_date, is_active, role, created_at
            FROM dbo.employees
            WHERE id = :id
        """), {"id": int(employee_id)}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")

    return dict(row)


@app.get("/employees/search")
def search_employees(q: str, x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    _get_user_by_key(x_employee_key)

    q = (q or "").strip()
    if len(q) < 2:
        return {"items": []}

    like = f"%{q}%"
    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT TOP 10
                id, full_name, email, phone
            FROM dbo.employees
            WHERE is_active = 1
              AND (
                  full_name LIKE :like
                  OR email LIKE :like
                  OR phone LIKE :like
              )
            ORDER BY full_name ASC
        """), {"like": like}).mappings().all()

    return {"items": [dict(r) for r in rows]}


@app.post("/employees")
def create_employee(
    full_name: str,
    office_country: str,
    position: str,
    email: str | None = None,
    phone: str | None = None,
    role: str = "employee",
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    if x_admin_key == ADMIN_KEY:
        pass
    else:
        _require_hr_or_admin(x_employee_key)

    role = (role or "employee").strip().lower()
    if role not in ("admin", "hr", "employee"):
        raise HTTPException(status_code=400, detail="Invalid role")

    raw_key = secrets.token_urlsafe(32)
    key_hash = _hash_key(raw_key)

    with engine.begin() as conn:
        res = conn.execute(sql("""
            INSERT INTO dbo.employees
                (full_name, phone, email, office_country, position, employment_date, key_hash, is_active, role)
            OUTPUT INSERTED.id
            VALUES
                (:full_name, :phone, :email, :office_country, :position,
                 CAST(GETDATE() AS date), :key_hash, 1, :role)
        """), {
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "office_country": office_country,
            "position": position,
            "key_hash": key_hash,
            "role": role,
        })
        employee_id = int(res.scalar())

    email_status = "not_sent"
    email_error = None

    if email:
        try:
            _send_account_email(email, full_name, raw_key, office_country, position)
            email_status = "sent"
        except Exception as e:
            email_status = "failed"
            email_error = str(e)
            print(f"[EMAIL ERROR] to={email}: {e}")

    return {
        "id": employee_id,
        "employee_key": raw_key,
        "email_status": email_status,
        "email_error": email_error,
        "note": "Save this key. It will not be shown again."
    }


@app.put("/employees/{employee_id}")
def update_employee(
    employee_id: int,
    full_name: str | None = None,
    office_country: str | None = None,
    position: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    is_active: int | None = None,
    role: str | None = None,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    _require_hr_or_admin(x_employee_key)

    with engine.begin() as conn:
        current = conn.execute(sql("""
            SELECT
                id, full_name, phone, email, office_country, position,
                employment_date, is_active, role
            FROM dbo.employees
            WHERE id = :id
        """), {"id": int(employee_id)}).mappings().first()

        if not current:
            raise HTTPException(status_code=404, detail="Employee not found")

        new_role = current["role"] if role is None else role.strip().lower()
        if new_role not in ("admin", "hr", "employee"):
            raise HTTPException(status_code=400, detail="Invalid role")

        new_is_active = current["is_active"] if is_active is None else int(is_active)
        if new_is_active not in (0, 1):
            raise HTTPException(status_code=400, detail="is_active must be 0 or 1")

        conn.execute(sql("""
            UPDATE dbo.employees
            SET
                full_name = COALESCE(:full_name, full_name),
                phone = COALESCE(:phone, phone),
                email = COALESCE(:email, email),
                office_country = COALESCE(:office_country, office_country),
                position = COALESCE(:position, position),
                is_active = :is_active,
                role = :role
            WHERE id = :id
        """), {
            "id": int(employee_id),
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "office_country": office_country,
            "position": position,
            "is_active": new_is_active,
            "role": new_role,
        })

        row = conn.execute(sql("""
            SELECT
                id, full_name, phone, email, office_country, position,
                employment_date, is_active, role, created_at
            FROM dbo.employees
            WHERE id = :id
        """), {"id": int(employee_id)}).mappings().first()

    return {"message": "employee updated", **dict(row)}


@app.post("/employees/{employee_id}/regenerate-key")
def regenerate_key(
    employee_id: int,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key"),
):
    _require_hr_or_admin(x_employee_key)

    raw_key = secrets.token_urlsafe(32)
    key_hash = _hash_key(raw_key)

    with engine.begin() as conn:
        current = conn.execute(sql("""
            SELECT id, full_name, email, office_country, position
            FROM dbo.employees
            WHERE id = :id
        """), {"id": int(employee_id)}).mappings().first()

        if not current:
            raise HTTPException(status_code=404, detail="Employee not found")

        conn.execute(sql("""
            UPDATE dbo.employees
            SET key_hash = :key_hash
            WHERE id = :id
        """), {
            "id": int(employee_id),
            "key_hash": key_hash,
        })

    email_status = "not_sent"
    email_error = None

    if current["email"]:
        try:
            _send_account_email(
                current["email"],
                current["full_name"],
                raw_key,
                current["office_country"],
                current["position"],
            )
            email_status = "sent"
        except Exception as e:
            email_status = "failed"
            email_error = str(e)
            print(f"[EMAIL ERROR] to={current['email']}: {e}")

    return {
        "message": "key regenerated",
        "id": int(current["id"]),
        "employee_key": raw_key,
        "email_status": email_status,
        "email_error": email_error,
    }