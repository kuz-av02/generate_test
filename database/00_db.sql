DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'test_generator') THEN
      PERFORM dblink_exec('dbname=postgres', 'CREATE DATABASE test_generator');
   END IF;
END
$do$;

\c test_generator;