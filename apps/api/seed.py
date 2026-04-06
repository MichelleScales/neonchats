"""
Run with: .venv/bin/python seed.py
Creates: tenant 'acme', role 'workspace_admin', user admin@acme.com / password123
"""
import uuid
import bcrypt
import psycopg2

pwd = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()

tenant_id = uuid.UUID("a0000000-0000-0000-0000-000000000001")
role_id   = uuid.UUID("b0000000-0000-0000-0000-000000000001")
user_id   = uuid.UUID("c0000000-0000-0000-0000-000000000001")
ur_id     = uuid.UUID("d0000000-0000-0000-0000-000000000001")

conn = psycopg2.connect("postgresql://emp:emp@localhost:5432/emp")
cur  = conn.cursor()

cur.execute("DELETE FROM user_roles WHERE id = %s", (str(ur_id),))
cur.execute("DELETE FROM users    WHERE id = %s", (str(user_id),))
cur.execute("DELETE FROM roles    WHERE id = %s", (str(role_id),))
cur.execute("DELETE FROM tenants  WHERE id = %s", (str(tenant_id),))

cur.execute(
    "INSERT INTO tenants (id, name, slug, plan, is_active) VALUES (%s,%s,%s,%s,%s)",
    (str(tenant_id), "Acme Corp", "acme", "starter", True),
)
cur.execute(
    "INSERT INTO roles (id, tenant_id, name, permissions) VALUES (%s,%s,%s,%s::jsonb)",
    (str(role_id), str(tenant_id), "workspace_admin", '["*"]'),
)
cur.execute(
    "INSERT INTO users (id, tenant_id, email, full_name, hashed_password, is_active) VALUES (%s,%s,%s,%s,%s,%s)",
    (str(user_id), str(tenant_id), "admin@acme.com", "Admin User", pwd, True),
)
cur.execute(
    "INSERT INTO user_roles (id, user_id, role_id) VALUES (%s,%s,%s)",
    (str(ur_id), str(user_id), str(role_id)),
)

conn.commit()
cur.close()
conn.close()
print("Seeded:")
print("  Workspace : acme")
print("  Email     : admin@acme.com")
print("  Password  : password123")
print("  Role      : workspace_admin")
