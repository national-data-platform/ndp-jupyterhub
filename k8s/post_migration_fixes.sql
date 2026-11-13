-- Run against JupyterHub's Postgres DB immediately after pgloader migration, before starting the hub.
-- Fixes type mismatches that pgloader introduces from SQLite which cause the hub to crashloop.

-- 1. Create id sequences (pgloader leaves id columns as plain bigint with no default)
DO $$
DECLARE
    r RECORD;
    max_id bigint;
    seq_name text;
BEGIN
    FOR r IN
        SELECT c.table_name
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.column_name = 'id'
          AND c.column_default IS NULL
          AND c.data_type IN ('integer', 'bigint')
    LOOP
        seq_name := r.table_name || '_id_seq';
        EXECUTE format('CREATE SEQUENCE IF NOT EXISTS %I', seq_name);
        EXECUTE format('SELECT COALESCE(MAX(id), 0) + 1 FROM %I', r.table_name) INTO max_id;
        EXECUTE format('SELECT setval(%L, %s)', seq_name, max_id);
        EXECUTE format('ALTER TABLE %I ALTER COLUMN id SET DEFAULT nextval(%L)', r.table_name, seq_name);
    END LOOP;
END $$;

-- 2. Fix boolean columns migrated as text
ALTER TABLE users ALTER COLUMN admin TYPE boolean
  USING CASE WHEN admin IN ('1', 'true', 't') THEN true ELSE false END;
ALTER TABLE services ALTER COLUMN admin TYPE boolean
  USING CASE WHEN admin IN ('1', 'true', 't') THEN true ELSE false END;
ALTER TABLE users_info ALTER COLUMN has_2fa TYPE boolean
  USING CASE WHEN has_2fa IN ('1', 'true', 't') THEN true ELSE false END;
ALTER TABLE users_info ALTER COLUMN is_authorized TYPE boolean
  USING CASE WHEN is_authorized IN ('1', 'true', 't') THEN true ELSE false END;
ALTER TABLE users_info ALTER COLUMN login_email_sent TYPE boolean
  USING CASE WHEN login_email_sent IN ('1', 'true', 't') THEN true ELSE false END;

-- 3. Fix timestamps: pgloader creates 'timestamp with time zone' but JupyterHub expects naive
ALTER TABLE users ALTER COLUMN created TYPE timestamp without time zone USING created AT TIME ZONE 'UTC';
ALTER TABLE users ALTER COLUMN last_activity TYPE timestamp without time zone USING last_activity AT TIME ZONE 'UTC';
ALTER TABLE spawners ALTER COLUMN last_activity TYPE timestamp without time zone USING last_activity AT TIME ZONE 'UTC';
ALTER TABLE spawners ALTER COLUMN started TYPE timestamp without time zone USING started AT TIME ZONE 'UTC';
ALTER TABLE api_tokens ALTER COLUMN created TYPE timestamp without time zone USING created AT TIME ZONE 'UTC';
ALTER TABLE api_tokens ALTER COLUMN last_activity TYPE timestamp without time zone USING last_activity AT TIME ZONE 'UTC';
ALTER TABLE api_tokens ALTER COLUMN expires_at TYPE timestamp without time zone USING expires_at AT TIME ZONE 'UTC';
