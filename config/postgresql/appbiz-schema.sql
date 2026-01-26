-- Schéma SQL pour l'application métier multi-base
-- Base de données: appbiz

CREATE DATABASE IF NOT EXISTS appbiz;
\c appbiz;

-- Table users
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    User_ldap_dn VARCHAR(100) NOT NULL,
    User_ldap_class VARCHAR(100) NOT NULL,
    user_id_ldap VARCHAR(100) NOT NULL,
    firstname VARCHAR(50) NOT NULL,
    lastname VARCHAR(50) NOT NULL,
    commonname VARCHAR(50) NOT NULL,
    email VARCHAR(50) NOT NULL UNIQUE,
    brithdate VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table profiles
CREATE TABLE IF NOT EXISTS profiles (
    profile_id SERIAL PRIMARY KEY,
    profile_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table user_profile_id_permissions
CREATE TABLE IF NOT EXISTS user_profile_id_permissions (
    urp_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    profile_id INT NOT NULL,
    permission_name VARCHAR(100) NOT NULL,
    is_allowed BOOLEAN DEFAULT TRUE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (profile_id) REFERENCES profiles(profile_id) ON DELETE CASCADE,
    UNIQUE(user_id, profile_id, permission_name)
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_ldap_dn ON users(User_ldap_dn);
CREATE INDEX IF NOT EXISTS idx_user_profile_user_id ON user_profile_id_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profile_profile_id ON user_profile_id_permissions(profile_id);

-- Insertion des profils de base
INSERT INTO profiles (profile_name, description) VALUES
    ('User', 'Profil utilisateur standard'),
    ('Manager', 'Profil manager'),
    ('Admin', 'Profil administrateur'),
    ('Audit', 'Profil audit')
ON CONFLICT (profile_name) DO NOTHING;

-- Fonction pour mettre à jour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger pour updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
