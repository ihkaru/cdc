import os
from sqlalchemy import create_engine, text

# Read cookie from file
cookie_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../tmp/new_vpn_cookie.txt")
)
with open(cookie_path, "r") as f:
    cookie_str = f.read().strip()

# Extract SVPNCOOKIE part if needed, or store full string
# Dashboard sync.ts stores cookie.trim() directly
db_url = os.getenv(
    "DATABASE_URL", "postgresql://fasih:fasih123@127.0.0.1:5432/fasih_dashboard"
)
engine = create_engine(db_url)

with engine.connect() as conn:
    query = text("""
        INSERT INTO system_settings (key, value, updated_at) 
        VALUES ('vpn_cookie', :val, NOW()) 
        ON CONFLICT (key) DO UPDATE 
        SET value = EXCLUDED.value, updated_at = NOW();
    """)
    conn.execute(query, {"val": cookie_str})
    conn.commit()

print(f"✅ Successfully injected fresh VPN cookie from {cookie_path} into database.")
