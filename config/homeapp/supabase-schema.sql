-- =============================================================================
-- Home App - Schéma Supabase (équivalent du schéma PostgreSQL local)
-- Ce fichier peut être exécuté dans le SQL Editor de Supabase
-- Projet IGA - Provisioning depuis MidPoint via Gateway
-- =============================================================================

-- Note: Supabase utilise déjà l'extension uuid-ossp par défaut
-- Les policies RLS seront configurées via le dashboard Supabase

-- =============================================================================
-- TABLES PRINCIPALES
-- =============================================================================

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    login VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(255) GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED,
    department VARCHAR(100),
    job_title VARCHAR(100),
    employee_number VARCHAR(50) UNIQUE,
    manager_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    midpoint_oid VARCHAR(36),
    source_system VARCHAR(50) DEFAULT 'midpoint',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ,
    attributes JSONB DEFAULT '{}'::jsonb
);

-- Table des permissions
CREATE TABLE IF NOT EXISTS public.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) UNIQUE NOT NULL,
    label VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    resource_type VARCHAR(100),
    action VARCHAR(50),
    is_sensitive BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table des rôles
CREATE TABLE IF NOT EXISTS public.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    is_sensitive BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT FALSE,
    approval_level INTEGER DEFAULT 0,
    midpoint_role_oid VARCHAR(36),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table de liaison rôle <-> permissions
CREATE TABLE IF NOT EXISTS public.role_permissions (
    role_id UUID REFERENCES public.roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES public.permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

-- Table de liaison utilisateur <-> rôles
CREATE TABLE IF NOT EXISTS public.user_roles (
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES public.roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by VARCHAR(100),
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    source VARCHAR(50) DEFAULT 'manual',
    PRIMARY KEY (user_id, role_id)
);

-- Table de liaison utilisateur <-> permissions directes
CREATE TABLE IF NOT EXISTS public.user_permissions (
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES public.permissions(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by VARCHAR(100),
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    reason TEXT,
    PRIMARY KEY (user_id, permission_id)
);

-- Table des demandes de provisioning
CREATE TABLE IF NOT EXISTS public.provisioning_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    target_user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    target_user_login VARCHAR(100),
    requested_role_id UUID REFERENCES public.roles(id) ON DELETE SET NULL,
    requested_permission_id UUID REFERENCES public.permissions(id) ON DELETE SET NULL,
    payload JSONB NOT NULL,
    requester_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    requester_name VARCHAR(255),
    justification TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    midpoint_case_oid VARCHAR(36),
    n8n_workflow_id VARCHAR(100)
);

-- Table des étapes d'approbation
CREATE TABLE IF NOT EXISTS public.approval_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES public.provisioning_requests(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    approver_type VARCHAR(50) NOT NULL,
    approver_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    approver_email VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    decision_at TIMESTAMPTZ,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table d'audit
CREATE TABLE IF NOT EXISTS public.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    event_timestamp TIMESTAMPTZ DEFAULT NOW(),
    actor_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    actor_name VARCHAR(255),
    target_type VARCHAR(50),
    target_id UUID,
    target_name VARCHAR(255),
    action VARCHAR(50),
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    source VARCHAR(50) DEFAULT 'supabase'
);

-- =============================================================================
-- INDEX
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_users_login ON public.users(login);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_department ON public.users(department);
CREATE INDEX IF NOT EXISTS idx_users_midpoint_oid ON public.users(midpoint_oid);
CREATE INDEX IF NOT EXISTS idx_permissions_code ON public.permissions(code);
CREATE INDEX IF NOT EXISTS idx_roles_code ON public.roles(code);
CREATE INDEX IF NOT EXISTS idx_provisioning_requests_status ON public.provisioning_requests(status);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON public.audit_log(event_timestamp);

-- =============================================================================
-- FONCTIONS (adaptées pour Supabase)
-- =============================================================================

-- Trigger pour updated_at
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers
DROP TRIGGER IF EXISTS on_users_updated ON public.users;
CREATE TRIGGER on_users_updated
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS on_roles_updated ON public.roles;
CREATE TRIGGER on_roles_updated
    BEFORE UPDATE ON public.roles
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS on_provisioning_requests_updated ON public.provisioning_requests;
CREATE TRIGGER on_provisioning_requests_updated
    BEFORE UPDATE ON public.provisioning_requests
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Fonction upsert user
CREATE OR REPLACE FUNCTION public.upsert_user(
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
    INSERT INTO public.users (login, email, password_hash, first_name, last_name, 
                       department, job_title, employee_number, is_active, 
                       midpoint_oid, attributes)
    VALUES (p_login, p_email, p_password_hash, p_first_name, p_last_name,
            p_department, p_job_title, p_employee_number, p_is_active,
            p_midpoint_oid, p_attributes)
    ON CONFLICT (login) DO UPDATE SET
        email = COALESCE(EXCLUDED.email, public.users.email),
        password_hash = COALESCE(EXCLUDED.password_hash, public.users.password_hash),
        first_name = COALESCE(EXCLUDED.first_name, public.users.first_name),
        last_name = COALESCE(EXCLUDED.last_name, public.users.last_name),
        department = COALESCE(EXCLUDED.department, public.users.department),
        job_title = COALESCE(EXCLUDED.job_title, public.users.job_title),
        employee_number = COALESCE(EXCLUDED.employee_number, public.users.employee_number),
        is_active = EXCLUDED.is_active,
        midpoint_oid = COALESCE(EXCLUDED.midpoint_oid, public.users.midpoint_oid),
        attributes = public.users.attributes || EXCLUDED.attributes
    RETURNING id INTO v_user_id;
    
    RETURN v_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour assigner un rôle
CREATE OR REPLACE FUNCTION public.assign_role_to_user(
    p_user_login VARCHAR,
    p_role_code VARCHAR,
    p_assigned_by VARCHAR DEFAULT 'system',
    p_source VARCHAR DEFAULT 'manual'
) RETURNS BOOLEAN AS $$
DECLARE
    v_user_id UUID;
    v_role_id UUID;
BEGIN
    SELECT id INTO v_user_id FROM public.users WHERE login = p_user_login;
    SELECT id INTO v_role_id FROM public.roles WHERE code = p_role_code;
    
    IF v_user_id IS NULL OR v_role_id IS NULL THEN
        RETURN FALSE;
    END IF;
    
    INSERT INTO public.user_roles (user_id, role_id, assigned_by, source)
    VALUES (v_user_id, v_role_id, p_assigned_by, p_source)
    ON CONFLICT (user_id, role_id) DO UPDATE SET
        assigned_by = EXCLUDED.assigned_by,
        assigned_at = NOW();
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour révoquer un rôle
CREATE OR REPLACE FUNCTION public.revoke_role_from_user(
    p_user_login VARCHAR,
    p_role_code VARCHAR
) RETURNS BOOLEAN AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM public.user_roles
    WHERE user_id = (SELECT id FROM public.users WHERE login = p_user_login)
    AND role_id = (SELECT id FROM public.roles WHERE code = p_role_code);
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted > 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Fonction pour obtenir les permissions effectives
CREATE OR REPLACE FUNCTION public.get_user_effective_permissions(p_user_login VARCHAR)
RETURNS TABLE (
    permission_code VARCHAR,
    permission_label VARCHAR,
    category VARCHAR,
    source VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        p.code::VARCHAR,
        p.label::VARCHAR,
        p.category::VARCHAR,
        ('role:' || r.code)::VARCHAR AS source
    FROM public.users u
    JOIN public.user_roles ur ON u.id = ur.user_id
    JOIN public.roles r ON ur.role_id = r.id
    JOIN public.role_permissions rp ON r.id = rp.role_id
    JOIN public.permissions p ON rp.permission_id = p.id
    WHERE u.login = p_user_login
    AND u.is_active = TRUE
    AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
    
    UNION
    
    SELECT DISTINCT
        p.code::VARCHAR,
        p.label::VARCHAR,
        p.category::VARCHAR,
        'direct'::VARCHAR AS source
    FROM public.users u
    JOIN public.user_permissions up ON u.id = up.user_id
    JOIN public.permissions p ON up.permission_id = p.id
    WHERE u.login = p_user_login
    AND u.is_active = TRUE
    AND (up.valid_until IS NULL OR up.valid_until > NOW());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) - À configurer selon vos besoins
-- =============================================================================

-- Activer RLS sur les tables sensibles
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- Policy par défaut: service_role peut tout faire (utilisé par la Gateway)
CREATE POLICY "Service role full access on users" ON public.users
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on audit_log" ON public.audit_log
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- DONNÉES INITIALES
-- =============================================================================

-- Permissions de base
INSERT INTO public.permissions (code, label, category, resource_type, action, is_sensitive) VALUES
    ('crm.read', 'Lecture CRM', 'crm', 'module', 'read', FALSE),
    ('crm.write', 'Écriture CRM', 'crm', 'module', 'write', FALSE),
    ('crm.delete', 'Suppression CRM', 'crm', 'module', 'delete', TRUE),
    ('crm.admin', 'Administration CRM', 'crm', 'module', 'admin', TRUE),
    ('hr.read', 'Lecture RH', 'hr', 'module', 'read', FALSE),
    ('hr.write', 'Écriture RH', 'hr', 'module', 'write', TRUE),
    ('hr.salary', 'Accès salaires', 'hr', 'data', 'read', TRUE),
    ('finance.read', 'Lecture Finance', 'finance', 'module', 'read', FALSE),
    ('finance.write', 'Écriture Finance', 'finance', 'module', 'write', TRUE),
    ('admin.users', 'Gestion utilisateurs', 'admin', 'users', 'admin', TRUE),
    ('admin.roles', 'Gestion rôles', 'admin', 'roles', 'admin', TRUE),
    ('intranet.access', 'Accès Intranet', 'intranet', 'module', 'read', FALSE)
ON CONFLICT (code) DO NOTHING;

-- Rôles de base
INSERT INTO public.roles (code, name, description, is_default, is_sensitive, requires_approval, approval_level) VALUES
    ('USER', 'Utilisateur standard', 'Accès de base', TRUE, FALSE, FALSE, 0),
    ('AGENT_COMMERCIAL', 'Agent Commercial', 'Accès au module CRM', FALSE, FALSE, FALSE, 0),
    ('RH_MANAGER', 'Responsable RH', 'Gestion RH complète', FALSE, TRUE, TRUE, 2),
    ('IT_ADMIN', 'Administrateur IT', 'Administration système', FALSE, TRUE, TRUE, 3)
ON CONFLICT (code) DO NOTHING;

-- Liaison rôles <-> permissions
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p 
WHERE r.code = 'USER' AND p.code IN ('intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p 
WHERE r.code = 'AGENT_COMMERCIAL' AND p.code IN ('crm.read', 'crm.write', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p 
WHERE r.code = 'RH_MANAGER' AND p.code IN ('hr.read', 'hr.write', 'hr.salary', 'intranet.access')
ON CONFLICT DO NOTHING;

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p 
WHERE r.code = 'IT_ADMIN' AND p.code IN ('admin.users', 'admin.roles', 'intranet.access')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- CONFIGURATION SUPABASE ADDITIONNELLE
-- =============================================================================
-- 
-- Après avoir exécuté ce script dans Supabase :
-- 
-- 1. Configurer les API keys dans le dashboard Supabase
-- 2. Récupérer l'URL du projet et la clé service_role
-- 3. Configurer ces valeurs dans la Gateway :
--    - SUPABASE_URL=https://votre-projet.supabase.co
--    - SUPABASE_SERVICE_KEY=eyJ...
-- 
-- 4. La Gateway utilisera le client Supabase pour :
--    - POST /rest/v1/users (création)
--    - PATCH /rest/v1/users?login=eq.xxx (mise à jour)
--    - Appel RPC: /rest/v1/rpc/upsert_user
--    - Appel RPC: /rest/v1/rpc/assign_role_to_user
-- =============================================================================

