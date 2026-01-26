-- =============================================================================
-- Home App - Schéma de base de données pour la gestion des identités
-- Projet IGA - Provisioning depuis MidPoint via Gateway
-- =============================================================================

-- Extension pour les UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- TABLES PRINCIPALES
-- =============================================================================

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    login VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(255) GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED,
    department VARCHAR(100),
    job_title VARCHAR(100),
    employee_number VARCHAR(50) UNIQUE,
    manager_id UUID REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    midpoint_oid VARCHAR(36),  -- OID de l'objet dans MidPoint
    source_system VARCHAR(50) DEFAULT 'midpoint',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    password_changed_at TIMESTAMP WITH TIME ZONE,
    attributes JSONB DEFAULT '{}'::jsonb  -- Attributs étendus flexibles
);

-- Table des permissions (granulaires)
CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(100) UNIQUE NOT NULL,
    label VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),  -- Ex: 'crm', 'hr', 'finance', 'admin'
    resource_type VARCHAR(100),  -- Ex: 'document', 'report', 'module'
    action VARCHAR(50),  -- Ex: 'read', 'write', 'delete', 'admin'
    is_sensitive BOOLEAN DEFAULT FALSE,  -- Nécessite approbation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table des rôles
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,  -- Assigné automatiquement aux nouveaux utilisateurs
    is_sensitive BOOLEAN DEFAULT FALSE,  -- Nécessite approbation
    requires_approval BOOLEAN DEFAULT FALSE,
    approval_level INTEGER DEFAULT 0,  -- 0=auto, 1=manager, 2=dept_head, 3=app_owner
    midpoint_role_oid VARCHAR(36),  -- OID du rôle correspondant dans MidPoint
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table de liaison rôle <-> permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

-- Table de liaison utilisateur <-> rôles
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(100),  -- Qui a assigné ce rôle (user/system/workflow)
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE,  -- NULL = pas d'expiration
    source VARCHAR(50) DEFAULT 'manual',  -- 'manual', 'midpoint', 'workflow', 'abac'
    PRIMARY KEY (user_id, role_id)
);

-- Table de liaison utilisateur <-> permissions directes (bypass rôles)
CREATE TABLE IF NOT EXISTS user_permissions (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(100),
    valid_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP WITH TIME ZONE,
    reason TEXT,  -- Justification de la permission directe
    PRIMARY KEY (user_id, permission_id)
);

-- =============================================================================
-- TABLES POUR LE WORKFLOW D'APPROBATION
-- =============================================================================

-- Table des demandes de provisioning (pour pré/post-provisioning)
CREATE TABLE IF NOT EXISTS provisioning_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_type VARCHAR(50) NOT NULL,  -- 'create_user', 'assign_role', 'assign_permission', 'remove_role'
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'completed', 'cancelled'
    target_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    target_user_login VARCHAR(100),  -- Pour les créations (user pas encore créé)
    requested_role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    requested_permission_id UUID REFERENCES permissions(id) ON DELETE SET NULL,
    payload JSONB NOT NULL,  -- Données complètes de la requête
    requester_id UUID REFERENCES users(id) ON DELETE SET NULL,
    requester_name VARCHAR(255),
    justification TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    midpoint_case_oid VARCHAR(36),  -- Référence au case MidPoint si applicable
    n8n_workflow_id VARCHAR(100)  -- ID du workflow N8N associé
);

-- Table des étapes d'approbation
CREATE TABLE IF NOT EXISTS approval_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID REFERENCES provisioning_requests(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    approver_type VARCHAR(50) NOT NULL,  -- 'manager', 'dept_head', 'app_owner', 'security'
    approver_id UUID REFERENCES users(id) ON DELETE SET NULL,
    approver_email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'skipped'
    decision_at TIMESTAMP WITH TIME ZONE,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table d'audit/historique
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_name VARCHAR(255),
    target_type VARCHAR(50),  -- 'user', 'role', 'permission', 'request'
    target_id UUID,
    target_name VARCHAR(255),
    action VARCHAR(50),  -- 'create', 'update', 'delete', 'assign', 'revoke', 'approve', 'reject'
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    source VARCHAR(50) DEFAULT 'homeapp'  -- 'homeapp', 'midpoint', 'n8n', 'api'
);

-- =============================================================================
-- INDEX
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_users_login ON users(login);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_department ON users(department);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_midpoint_oid ON users(midpoint_oid);
CREATE INDEX IF NOT EXISTS idx_users_employee_number ON users(employee_number);

CREATE INDEX IF NOT EXISTS idx_permissions_code ON permissions(code);
CREATE INDEX IF NOT EXISTS idx_permissions_category ON permissions(category);

CREATE INDEX IF NOT EXISTS idx_roles_code ON roles(code);

CREATE INDEX IF NOT EXISTS idx_provisioning_requests_status ON provisioning_requests(status);
CREATE INDEX IF NOT EXISTS idx_provisioning_requests_target_user ON provisioning_requests(target_user_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_target ON audit_log(target_type, target_id);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Fonction pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers pour updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_provisioning_requests_updated_at
    BEFORE UPDATE ON provisioning_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- FONCTIONS API (utilisées par la Gateway)
-- =============================================================================

-- Créer ou mettre à jour un utilisateur (upsert)
CREATE OR REPLACE FUNCTION upsert_user(
    p_login VARCHAR,
    p_email VARCHAR,
    p_password_hash VARCHAR DEFAULT NULL,
    p_first_name VARCHAR DEFAULT NULL,
    p_last_name VARCHAR DEFAULT NULL,
    p_department VARCHAR DEFAULT NULL,
    p_job_title VARCHAR DEFAULT NULL,
    p_employee_number VARCHAR DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT TRUE,
    p_midpoint_oid VARCHAR DEFAULT NULL,
    p_attributes JSONB DEFAULT '{}'::jsonb
) RETURNS UUID AS $$
DECLARE
    v_user_id UUID;
BEGIN
    INSERT INTO users (login, email, password_hash, first_name, last_name, 
                       department, job_title, employee_number, is_active, 
                       midpoint_oid, attributes)
    VALUES (p_login, p_email, p_password_hash, p_first_name, p_last_name,
            p_department, p_job_title, p_employee_number, p_is_active,
            p_midpoint_oid, p_attributes)
    ON CONFLICT (login) DO UPDATE SET
        email = COALESCE(EXCLUDED.email, users.email),
        password_hash = COALESCE(EXCLUDED.password_hash, users.password_hash),
        first_name = COALESCE(EXCLUDED.first_name, users.first_name),
        last_name = COALESCE(EXCLUDED.last_name, users.last_name),
        department = COALESCE(EXCLUDED.department, users.department),
        job_title = COALESCE(EXCLUDED.job_title, users.job_title),
        employee_number = COALESCE(EXCLUDED.employee_number, users.employee_number),
        is_active = EXCLUDED.is_active,
        midpoint_oid = COALESCE(EXCLUDED.midpoint_oid, users.midpoint_oid),
        attributes = users.attributes || EXCLUDED.attributes
    RETURNING id INTO v_user_id;
    
    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql;

-- Assigner un rôle à un utilisateur
CREATE OR REPLACE FUNCTION assign_role_to_user(
    p_user_login VARCHAR,
    p_role_code VARCHAR,
    p_assigned_by VARCHAR DEFAULT 'system',
    p_source VARCHAR DEFAULT 'manual',
    p_valid_until TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_user_id UUID;
    v_role_id UUID;
BEGIN
    SELECT id INTO v_user_id FROM users WHERE login = p_user_login;
    SELECT id INTO v_role_id FROM roles WHERE code = p_role_code;
    
    IF v_user_id IS NULL OR v_role_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    INSERT INTO user_roles (user_id, role_id, assigned_by, source, valid_until)
    VALUES (v_user_id, v_role_id, p_assigned_by, p_source, p_valid_until)
    ON CONFLICT (user_id, role_id) DO UPDATE SET
        assigned_by = EXCLUDED.assigned_by,
        valid_until = EXCLUDED.valid_until,
        assigned_at = CURRENT_TIMESTAMP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Révoquer un rôle d'un utilisateur
CREATE OR REPLACE FUNCTION revoke_role_from_user(
    p_user_login VARCHAR,
    p_role_code VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM user_roles
    WHERE user_id = (SELECT id FROM users WHERE login = p_user_login)
    AND role_id = (SELECT id FROM roles WHERE code = p_role_code);
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted > 0;
END;
$$ LANGUAGE plpgsql;

-- Assigner une permission directe à un utilisateur
CREATE OR REPLACE FUNCTION assign_permission_to_user(
    p_user_login VARCHAR,
    p_permission_code VARCHAR,
    p_assigned_by VARCHAR DEFAULT 'system',
    p_reason TEXT DEFAULT NULL,
    p_valid_until TIMESTAMP WITH TIME ZONE DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_user_id UUID;
    v_permission_id UUID;
BEGIN
    SELECT id INTO v_user_id FROM users WHERE login = p_user_login;
    SELECT id INTO v_permission_id FROM permissions WHERE code = p_permission_code;
    
    IF v_user_id IS NULL OR v_permission_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    INSERT INTO user_permissions (user_id, permission_id, assigned_by, reason, valid_until)
    VALUES (v_user_id, v_permission_id, p_assigned_by, p_reason, p_valid_until)
    ON CONFLICT (user_id, permission_id) DO UPDATE SET
        assigned_by = EXCLUDED.assigned_by,
        reason = EXCLUDED.reason,
        valid_until = EXCLUDED.valid_until,
        assigned_at = CURRENT_TIMESTAMP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Révoquer une permission directe
CREATE OR REPLACE FUNCTION revoke_permission_from_user(
    p_user_login VARCHAR,
    p_permission_code VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM user_permissions
    WHERE user_id = (SELECT id FROM users WHERE login = p_user_login)
    AND permission_id = (SELECT id FROM permissions WHERE code = p_permission_code);
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted > 0;
END;
$$ LANGUAGE plpgsql;

-- Obtenir toutes les permissions effectives d'un utilisateur
CREATE OR REPLACE FUNCTION get_user_effective_permissions(p_user_login VARCHAR)
RETURNS TABLE (
    permission_code VARCHAR,
    permission_label VARCHAR,
    category VARCHAR,
    source VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    -- Permissions via rôles
    SELECT DISTINCT
        p.code::VARCHAR,
        p.label::VARCHAR,
        p.category::VARCHAR,
        'role:' || r.code AS source
    FROM users u
    JOIN user_roles ur ON u.id = ur.user_id
    JOIN roles r ON ur.role_id = r.id
    JOIN role_permissions rp ON r.id = rp.role_id
    JOIN permissions p ON rp.permission_id = p.id
    WHERE u.login = p_user_login
    AND u.is_active = TRUE
    AND (ur.valid_until IS NULL OR ur.valid_until > CURRENT_TIMESTAMP)
    
    UNION
    
    -- Permissions directes
    SELECT DISTINCT
        p.code::VARCHAR,
        p.label::VARCHAR,
        p.category::VARCHAR,
        'direct' AS source
    FROM users u
    JOIN user_permissions up ON u.id = up.user_id
    JOIN permissions p ON up.permission_id = p.id
    WHERE u.login = p_user_login
    AND u.is_active = TRUE
    AND (up.valid_until IS NULL OR up.valid_until > CURRENT_TIMESTAMP);
END;
$$ LANGUAGE plpgsql;

-- Vérifier si un utilisateur a une permission
CREATE OR REPLACE FUNCTION user_has_permission(
    p_user_login VARCHAR,
    p_permission_code VARCHAR
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM get_user_effective_permissions(p_user_login)
        WHERE permission_code = p_permission_code
    );
END;
$$ LANGUAGE plpgsql;

-- Désactiver un utilisateur
CREATE OR REPLACE FUNCTION disable_user(p_user_login VARCHAR) RETURNS BOOLEAN AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE users SET is_active = FALSE WHERE login = p_user_login;
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END;
$$ LANGUAGE plpgsql;

-- Activer un utilisateur
CREATE OR REPLACE FUNCTION enable_user(p_user_login VARCHAR) RETURNS BOOLEAN AS $$
DECLARE
    v_updated INTEGER;
BEGIN
    UPDATE users SET is_active = TRUE WHERE login = p_user_login;
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    RETURN v_updated > 0;
END;
$$ LANGUAGE plpgsql;

-- Supprimer un utilisateur
CREATE OR REPLACE FUNCTION delete_user(p_user_login VARCHAR) RETURNS BOOLEAN AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM users WHERE login = p_user_login;
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted > 0;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VUES
-- =============================================================================

-- Vue des utilisateurs avec leurs rôles
CREATE OR REPLACE VIEW v_users_with_roles AS
SELECT 
    u.id,
    u.login,
    u.email,
    u.full_name,
    u.department,
    u.job_title,
    u.is_active,
    u.midpoint_oid,
    u.created_at,
    COALESCE(STRING_AGG(DISTINCT r.code, ', ' ORDER BY r.code), '') AS role_codes,
    COALESCE(STRING_AGG(DISTINCT r.name, ', ' ORDER BY r.name), '') AS role_names
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id 
    AND (ur.valid_until IS NULL OR ur.valid_until > CURRENT_TIMESTAMP)
LEFT JOIN roles r ON ur.role_id = r.id
GROUP BY u.id, u.login, u.email, u.full_name, u.department, u.job_title, 
         u.is_active, u.midpoint_oid, u.created_at;

-- Vue des demandes de provisioning en attente
CREATE OR REPLACE VIEW v_pending_requests AS
SELECT 
    pr.id,
    pr.request_type,
    pr.status,
    pr.target_user_login,
    u.full_name AS target_user_name,
    r.name AS requested_role_name,
    p.label AS requested_permission_label,
    pr.requester_name,
    pr.justification,
    pr.created_at,
    COUNT(DISTINCT CASE WHEN ast.status = 'pending' THEN ast.id END) AS pending_approvals,
    COUNT(DISTINCT CASE WHEN ast.status = 'approved' THEN ast.id END) AS completed_approvals
FROM provisioning_requests pr
LEFT JOIN users u ON pr.target_user_id = u.id
LEFT JOIN roles r ON pr.requested_role_id = r.id
LEFT JOIN permissions p ON pr.requested_permission_id = p.id
LEFT JOIN approval_steps ast ON pr.id = ast.request_id
WHERE pr.status = 'pending'
GROUP BY pr.id, pr.request_type, pr.status, pr.target_user_login, u.full_name,
         r.name, p.label, pr.requester_name, pr.justification, pr.created_at;

-- =============================================================================
-- DONNÉES INITIALES
-- =============================================================================

-- Permissions de base
INSERT INTO permissions (code, label, category, resource_type, action, is_sensitive) VALUES
    -- CRM
    ('crm.read', 'Lecture CRM', 'crm', 'module', 'read', FALSE),
    ('crm.write', 'Écriture CRM', 'crm', 'module', 'write', FALSE),
    ('crm.delete', 'Suppression CRM', 'crm', 'module', 'delete', TRUE),
    ('crm.admin', 'Administration CRM', 'crm', 'module', 'admin', TRUE),
    ('crm.export', 'Export données CRM', 'crm', 'data', 'export', TRUE),
    -- RH
    ('hr.read', 'Lecture RH', 'hr', 'module', 'read', FALSE),
    ('hr.write', 'Écriture RH', 'hr', 'module', 'write', TRUE),
    ('hr.salary', 'Accès salaires', 'hr', 'data', 'read', TRUE),
    ('hr.admin', 'Administration RH', 'hr', 'module', 'admin', TRUE),
    -- Finance
    ('finance.read', 'Lecture Finance', 'finance', 'module', 'read', FALSE),
    ('finance.write', 'Écriture Finance', 'finance', 'module', 'write', TRUE),
    ('finance.validate', 'Validation paiements', 'finance', 'transaction', 'validate', TRUE),
    ('finance.admin', 'Administration Finance', 'finance', 'module', 'admin', TRUE),
    -- IT / Admin
    ('admin.users', 'Gestion utilisateurs', 'admin', 'users', 'admin', TRUE),
    ('admin.roles', 'Gestion rôles', 'admin', 'roles', 'admin', TRUE),
    ('admin.system', 'Administration système', 'admin', 'system', 'admin', TRUE),
    ('admin.audit', 'Consultation audit', 'admin', 'audit', 'read', TRUE),
    -- Intranet général
    ('intranet.access', 'Accès Intranet', 'intranet', 'module', 'read', FALSE),
    ('intranet.documents', 'Accès documents', 'intranet', 'documents', 'read', FALSE),
    ('intranet.announcements', 'Publication annonces', 'intranet', 'announcements', 'write', FALSE),
    -- =============================================================================
    -- PERMISSIONS APPLICATION MÉTIER (Ressource 3 - PostgreSQL)
    -- =============================================================================
    ('app_read', 'Lecture application métier', 'app_metier', 'database', 'read', FALSE),
    ('app_write', 'Écriture application métier', 'app_metier', 'database', 'write', FALSE),
    ('app_admin_db', 'Administration base de données (CRITIQUE)', 'app_metier', 'database', 'admin', TRUE),
    -- =============================================================================
    -- PERMISSIONS ODOO ERP (Ressource 2)
    -- =============================================================================
    ('odoo.access', 'Accès Odoo ERP', 'odoo', 'erp', 'read', FALSE),
    ('odoo.finance', 'Module Finance Odoo', 'odoo', 'erp', 'write', FALSE),
    ('odoo.admin', 'Administration Odoo (CRITIQUE)', 'odoo', 'erp', 'admin', TRUE)
ON CONFLICT (code) DO NOTHING;

-- Rôles de base
INSERT INTO roles (code, name, description, is_default, is_sensitive, requires_approval, approval_level) VALUES
    ('USER', 'Utilisateur standard', 'Accès de base à l''intranet', TRUE, FALSE, FALSE, 0),
    ('AGENT_COMMERCIAL', 'Agent Commercial', 'Accès au module CRM pour la gestion des clients', FALSE, FALSE, FALSE, 0),
    ('COMMERCIAL_MANAGER', 'Responsable Commercial', 'Gestion d''équipe commerciale et rapports', FALSE, FALSE, TRUE, 1),
    ('RH_ASSISTANT', 'Assistant RH', 'Accès aux données RH en lecture', FALSE, FALSE, FALSE, 0),
    ('RH_MANAGER', 'Responsable RH', 'Gestion complète des ressources humaines', FALSE, TRUE, TRUE, 2),
    ('COMPTABLE', 'Comptable', 'Accès au module comptabilité', FALSE, FALSE, FALSE, 0),
    ('FINANCE_MANAGER', 'Responsable Finance', 'Validation des paiements et rapports financiers', FALSE, TRUE, TRUE, 2),
    ('IT_SUPPORT', 'Support IT', 'Support technique niveau 1', FALSE, FALSE, FALSE, 0),
    ('IT_ADMIN', 'Administrateur IT', 'Administration complète du système', FALSE, TRUE, TRUE, 3),
    ('MANAGER', 'Manager', 'Responsable avec droits de validation d''équipe', FALSE, FALSE, TRUE, 1),
    ('DIRECTOR', 'Directeur', 'Direction avec accès étendu', FALSE, TRUE, TRUE, 2),
    -- =============================================================================
    -- RÔLES APPLICATION MÉTIER (Ressource 3)
    -- =============================================================================
    ('APP_READ', 'Lecteur App Métier', 'Accès en lecture seule à l''application métier', FALSE, FALSE, FALSE, 0),
    ('APP_WRITE', 'Contributeur App Métier', 'Accès en lecture/écriture à l''application métier', FALSE, FALSE, FALSE, 0),
    ('APP_ADMIN_DB', 'Admin BDD App Métier', 'Administration de la base de données (CRITIQUE)', FALSE, TRUE, TRUE, 3),
    -- =============================================================================
    -- RÔLES ODOO ERP (Ressource 2)
    -- =============================================================================
    ('ODOO_USER', 'Utilisateur Odoo', 'Utilisateur standard Odoo ERP', FALSE, FALSE, FALSE, 0),
    ('ODOO_FINANCE', 'Finance Odoo', 'Accès module Finance Odoo', FALSE, FALSE, TRUE, 1),
    ('ODOO_ADMIN', 'Admin Odoo', 'Administrateur Odoo ERP (CRITIQUE)', FALSE, TRUE, TRUE, 3)
ON CONFLICT (code) DO NOTHING;

-- Liaison rôles <-> permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'USER' AND p.code IN ('intranet.access', 'intranet.documents')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'AGENT_COMMERCIAL' AND p.code IN ('crm.read', 'crm.write', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'COMMERCIAL_MANAGER' AND p.code IN ('crm.read', 'crm.write', 'crm.export', 'intranet.access', 'intranet.announcements')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'RH_ASSISTANT' AND p.code IN ('hr.read', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'RH_MANAGER' AND p.code IN ('hr.read', 'hr.write', 'hr.salary', 'hr.admin', 'intranet.access', 'intranet.announcements')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'COMPTABLE' AND p.code IN ('finance.read', 'finance.write', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'FINANCE_MANAGER' AND p.code IN ('finance.read', 'finance.write', 'finance.validate', 'finance.admin', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'IT_SUPPORT' AND p.code IN ('admin.users', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'IT_ADMIN' AND p.code IN ('admin.users', 'admin.roles', 'admin.system', 'admin.audit', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'MANAGER' AND p.code IN ('intranet.access', 'intranet.documents', 'intranet.announcements')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'DIRECTOR' AND p.code IN ('intranet.access', 'intranet.documents', 'intranet.announcements', 'hr.read', 'finance.read')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- LIAISON RÔLES <-> PERMISSIONS : APPLICATION MÉTIER (Ressource 3)
-- =============================================================================

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'APP_READ' AND p.code IN ('app_read', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'APP_WRITE' AND p.code IN ('app_read', 'app_write', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'APP_ADMIN_DB' AND p.code IN ('app_read', 'app_write', 'app_admin_db', 'intranet.access', 'admin.audit')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- LIAISON RÔLES <-> PERMISSIONS : ODOO ERP (Ressource 2)
-- =============================================================================

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'ODOO_USER' AND p.code IN ('odoo.access', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'ODOO_FINANCE' AND p.code IN ('odoo.access', 'odoo.finance', 'finance.read', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p WHERE r.code = 'ODOO_ADMIN' AND p.code IN ('odoo.access', 'odoo.finance', 'odoo.admin', 'admin.users', 'intranet.access')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- MESSAGE DE CONFIRMATION
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '====================================================';
    RAISE NOTICE 'Home App Database initialized successfully!';
    RAISE NOTICE '- Users table ready';
    RAISE NOTICE '- Permissions: % created', (SELECT COUNT(*) FROM permissions);
    RAISE NOTICE '- Roles: % created', (SELECT COUNT(*) FROM roles);
    RAISE NOTICE '- Ready for MidPoint provisioning via Gateway';
    RAISE NOTICE '====================================================';
END $$;

