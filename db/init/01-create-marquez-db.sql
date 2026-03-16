DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'marquez') THEN
      CREATE ROLE marquez LOGIN PASSWORD 'marquez';
   ELSE
      ALTER ROLE marquez WITH LOGIN PASSWORD 'marquez';
   END IF;
END
$do$;

SELECT 'CREATE DATABASE marquez OWNER marquez'
WHERE NOT EXISTS (
    SELECT
    FROM pg_database
    WHERE datname = 'marquez'
)\gexec

GRANT ALL PRIVILEGES ON DATABASE marquez TO marquez;
