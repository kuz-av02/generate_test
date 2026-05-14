CREATE INDEX IF NOT EXISTS idx_generations_user_id ON generations(user_id);
CREATE INDEX IF NOT EXISTS idx_generations_created_at ON generations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generations_parent_id ON generations(parent_id);

-- НОВЫЕ индексы
CREATE INDEX IF NOT EXISTS idx_generations_model_used ON generations(model_used);
CREATE INDEX IF NOT EXISTS idx_generations_version ON generations(version);

-- Индекс для generation_logs
CREATE INDEX IF NOT EXISTS idx_generation_logs_request_id ON generation_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_generation_logs_model_used ON generation_logs(model_used);

-- Индекс для users
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);