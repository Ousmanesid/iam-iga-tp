-- =============================================================================
-- Script d'initialisation de la base de données Intranet
-- Pour le projet IGA - Provisionnement depuis MidPoint
-- =============================================================================

-- Table des utilisateurs de l'application intranet
CREATE TABLE IF NOT EXISTS app_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(255),
    department VARCHAR(100),
    title VARCHAR(100),
    employee_number VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Table des rôles applicatifs
CREATE TABLE IF NOT EXISTS app_roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table d'association utilisateurs-rôles
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER REFERENCES app_users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES app_roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Insertion des rôles par défaut
INSERT INTO app_roles (role_name, description) VALUES
    ('USER', 'Utilisateur standard avec accès basique'),
    ('AGENT_COMMERCIAL', 'Agent commercial avec accès au module CRM'),
    ('RH_MANAGER', 'Responsable RH avec accès aux données employés'),
    ('IT_ADMIN', 'Administrateur IT avec accès complet'),
    ('COMPTABLE', 'Accès au module comptabilité'),
    ('MANAGER', 'Responsable avec droits de validation')
ON CONFLICT (role_name) DO NOTHING;

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_app_users_username ON app_users(username);
CREATE INDEX IF NOT EXISTS idx_app_users_email ON app_users(email);
CREATE INDEX IF NOT EXISTS idx_app_users_department ON app_users(department);
CREATE INDEX IF NOT EXISTS idx_app_users_enabled ON app_users(enabled);

-- Fonction pour mettre à jour le timestamp updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger pour mettre à jour automatiquement updated_at
DROP TRIGGER IF EXISTS update_app_users_updated_at ON app_users;
CREATE TRIGGER update_app_users_updated_at
    BEFORE UPDATE ON app_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Vue pour lister les utilisateurs avec leurs rôles
CREATE OR REPLACE VIEW v_users_with_roles AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.full_name,
    u.department,
    u.enabled,
    STRING_AGG(r.role_name, ', ' ORDER BY r.role_name) as roles
FROM app_users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN app_roles r ON ur.role_id = r.id
GROUP BY u.id, u.username, u.email, u.full_name, u.department, u.enabled;

-- Procédure pour créer ou mettre à jour un utilisateur (upsert)
-- Gère les conflits sur username ET email
CREATE OR REPLACE FUNCTION upsert_user(
    p_username VARCHAR,
    p_email VARCHAR,
    p_first_name VARCHAR,
    p_last_name VARCHAR,
    p_department VARCHAR,
    p_title VARCHAR,
    p_employee_number VARCHAR,
    p_enabled BOOLEAN
) RETURNS INTEGER AS $$
DECLARE
    v_user_id INTEGER;
    v_existing_id INTEGER;
BEGIN
    -- Vérifier si un utilisateur existe déjà avec cet email (mais username différent)
    SELECT id INTO v_existing_id FROM app_users WHERE email = p_email AND username != p_username;
    
    IF v_existing_id IS NOT NULL THEN
        -- Mettre à jour l'utilisateur existant avec le nouvel username
        UPDATE app_users SET
            username = p_username,
            first_name = p_first_name,
            last_name = p_last_name,
            full_name = p_first_name || ' ' || p_last_name,
            department = p_department,
            title = p_title,
            employee_number = p_employee_number,
            enabled = p_enabled
        WHERE id = v_existing_id
        RETURNING id INTO v_user_id;
    ELSE
        -- Upsert normal basé sur username
        INSERT INTO app_users (username, email, first_name, last_name, full_name, department, title, employee_number, enabled)
        VALUES (p_username, p_email, p_first_name, p_last_name, p_first_name || ' ' || p_last_name, p_department, p_title, p_employee_number, p_enabled)
        ON CONFLICT (username) DO UPDATE SET
            email = EXCLUDED.email,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            full_name = EXCLUDED.full_name,
            department = EXCLUDED.department,
            title = EXCLUDED.title,
            employee_number = EXCLUDED.employee_number,
            enabled = EXCLUDED.enabled
        RETURNING id INTO v_user_id;
    END IF;
    
    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;

-- Procédure pour assigner un rôle à un utilisateur
CREATE OR REPLACE FUNCTION assign_role(
    p_username VARCHAR,
    p_role_name VARCHAR
) RETURNS VOID AS $$
DECLARE
    v_user_id INTEGER;
    v_role_id INTEGER;
BEGIN
    SELECT id INTO v_user_id FROM app_users WHERE username = p_username;
    SELECT id INTO v_role_id FROM app_roles WHERE role_name = p_role_name;
    
    IF v_user_id IS NOT NULL AND v_role_id IS NOT NULL THEN
        INSERT INTO user_roles (user_id, role_id)
        VALUES (v_user_id, v_role_id)
        ON CONFLICT DO NOTHING;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Procédure pour révoquer un rôle
CREATE OR REPLACE FUNCTION revoke_role(
    p_username VARCHAR,
    p_role_name VARCHAR
) RETURNS VOID AS $$
BEGIN
    DELETE FROM user_roles
    WHERE user_id = (SELECT id FROM app_users WHERE username = p_username)
    AND role_id = (SELECT id FROM app_roles WHERE role_name = p_role_name);
END;
$$ LANGUAGE plpgsql;

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Base de données Intranet initialisée avec succès!';
END $$;

