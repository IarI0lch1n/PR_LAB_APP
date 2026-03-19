import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

def make_engine():
    host = os.getenv("DB_HOST", "host.docker.internal")
    port = os.getenv("DB_PORT", "1433")
    name = os.getenv("DB_NAME", "PR_LAB_APP")
    user = os.getenv("DB_USER", "pr_user")
    pwd  = os.getenv("DB_PASS", "")
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    odbc = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={name};"
        f"UID={user};PWD={pwd};"
        f"Encrypt=no;"
        f"TrustServerCertificate=yes;"
    )
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}",
        pool_pre_ping=True
    )

engine = make_engine()