from __future__ import annotations

import os
import secrets
import bcrypt
from fastapi import FastAPI, Header, HTTPException
from sqlalchemy import text as sql

from .db import engine

app = FastAPI(title="Account API", version="1.0")

ADMIN_KEY = os.getenv("ACCOUNT_ADMIN_KEY", "admin-dev-key")


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


@app.post("/employees")
def create_employee(
    full_name: str,
    office_country: str,
    position: str,
    email: str | None = None,
    phone: str | None = None,
    employment_date: str | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="X-Admin-Key required")

    with engine.begin() as conn:
        # получить ключ из процедуры
        row = conn.execute(sql("""
            DECLARE @k NVARCHAR(64);
            EXEC dbo.sp_generate_employee_key @key=@k OUTPUT;
            SELECT @k AS employee_key;
        """)).mappings().first()

    raw_key = row["employee_key"]
    key_hash = _hash_key(raw_key)

    with engine.begin() as conn:
        res = conn.execute(sql("""
            INSERT INTO dbo.employees
              (full_name, phone, email, office_country, position, employment_date, key_hash, is_active)
            OUTPUT INSERTED.id
            VALUES
              (:full_name, :phone, :email, :office_country, :position,
               COALESCE(TRY_CONVERT(date, :employment_date), CAST(GETDATE() AS date)),
               :key_hash, 1)
        """), {
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "office_country": office_country,
            "position": position,
            "employment_date": employment_date,
            "key_hash": key_hash
        })
        employee_id = int(res.scalar())

    return {
        "id": employee_id,
        "employee_key": raw_key,
        "note": "Save this key. It will not be shown again."
    }


@app.post("/auth/verify")
def verify_key(x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    if not x_employee_key:
        raise HTTPException(status_code=401, detail="X-Employee-Key required")

    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT id, full_name, phone, email, office_country, position, employment_date, key_hash, is_active
            FROM dbo.employees
            WHERE is_active = 1
        """)).mappings().all()

    for r in rows:
        if _check_key(x_employee_key, r["key_hash"]):
            return {
                "id": int(r["id"]),
                "full_name": r["full_name"],
                "phone": r["phone"],
                "email": r["email"],
                "office_country": r["office_country"],
                "position": r["position"],
                "employment_date": str(r["employment_date"]),
            }

    raise HTTPException(status_code=401, detail="Invalid employee key")


@app.get("/me")
def me(x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")):
    return verify_key(x_employee_key)


@app.get("/employees/search")
def search_employees(
    q: str,
    x_employee_key: str | None = Header(default=None, alias="X-Employee-Key")
):
    # просто проверяем что ключ валидный (кто ищет)
    _ = verify_key(x_employee_key)

    q = (q or "").strip()
    if len(q) < 2:
        return {"items": []}

    like = f"%{q}%"
    with engine.connect() as conn:
        rows = conn.execute(sql("""
            SELECT TOP 10 id, full_name, email, phone
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