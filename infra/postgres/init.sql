-- Extensions used by ZMetrics
-- uuid-ossp: server-side UUID generation (gen_random_uuid is from pgcrypto/core, but uuid-ossp is explicit)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pg_trgm: trigram index for future full-text search on notes, names
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- btree_gin: for GIN indexes on composite columns (optional, useful for JSONB + B-tree combos)
CREATE EXTENSION IF NOT EXISTS "btree_gin";
