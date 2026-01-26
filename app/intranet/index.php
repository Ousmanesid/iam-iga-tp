<?php
/**
 * Application Intranet - Interface principale
 * Projet IGA - Gestion des identités et des accès
 */

// Configuration base de données
$db_host = getenv('DB_HOST') ?: 'intranet-db';
$db_name = getenv('DB_NAME') ?: 'intranet';
$db_user = getenv('DB_USER') ?: 'intranet';
$db_pass = getenv('DB_PASS') ?: 'intranet123';

// Connexion PostgreSQL
try {
    $pdo = new PDO(
        "pgsql:host=$db_host;dbname=$db_name",
        $db_user,
        $db_pass,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
} catch (PDOException $e) {
    $db_error = $e->getMessage();
}

// Récupérer les statistiques
$stats = [];
if (isset($pdo)) {
    try {
        $stats['total_users'] = $pdo->query("SELECT COUNT(*) FROM app_users")->fetchColumn();
        $stats['active_users'] = $pdo->query("SELECT COUNT(*) FROM app_users WHERE enabled = true")->fetchColumn();
        $stats['total_roles'] = $pdo->query("SELECT COUNT(*) FROM app_roles")->fetchColumn();
        
        $dept_query = $pdo->query("SELECT department, COUNT(*) as count FROM app_users GROUP BY department ORDER BY count DESC");
        $stats['by_department'] = $dept_query->fetchAll(PDO::FETCH_ASSOC);
        
        $users_query = $pdo->query("SELECT * FROM v_users_with_roles ORDER BY full_name LIMIT 50");
        $users = $users_query->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        $query_error = $e->getMessage();
    }
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Intranet - Gestion des utilisateurs</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-700: #374151;
            --gray-900: #111827;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        header h1 {
            font-size: 1.75rem;
            color: var(--gray-900);
        }
        
        header h1 span {
            color: var(--primary);
        }
        
        .badge {
            background: var(--primary);
            color: white;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }
        
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .stat-card h3 {
            font-size: 0.875rem;
            color: var(--gray-700);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stat-card .value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--gray-900);
        }
        
        .stat-card.success .value { color: var(--success); }
        .stat-card.warning .value { color: var(--warning); }
        .stat-card.primary .value { color: var(--primary); }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 24px;
        }
        
        @media (max-width: 1024px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .card h2 {
            font-size: 1.25rem;
            color: var(--gray-900);
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--gray-100);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--gray-100);
        }
        
        th {
            background: var(--gray-50);
            font-weight: 600;
            color: var(--gray-700);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        tr:hover {
            background: var(--gray-50);
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .status-badge.active {
            background: #d1fae5;
            color: #065f46;
        }
        
        .status-badge.inactive {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .status-badge::before {
            content: '';
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }
        
        .status-badge.active::before {
            background: #10b981;
        }
        
        .status-badge.inactive::before {
            background: #ef4444;
        }
        
        .role-tag {
            display: inline-block;
            background: var(--gray-100);
            color: var(--gray-700);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            margin: 2px;
        }
        
        .role-tag.special {
            background: #dbeafe;
            color: #1e40af;
        }
        
        .dept-list {
            list-style: none;
        }
        
        .dept-list li {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid var(--gray-100);
        }
        
        .dept-list li:last-child {
            border-bottom: none;
        }
        
        .dept-count {
            background: var(--primary);
            color: white;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .error {
            background: #fee2e2;
            border: 1px solid #fecaca;
            color: #991b1b;
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .info-box {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            color: #1e40af;
            padding: 16px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 0.875rem;
        }
        
        .info-box strong {
            display: block;
            margin-bottom: 8px;
        }
        
        footer {
            text-align: center;
            color: white;
            padding: 20px;
            margin-top: 24px;
            font-size: 0.875rem;
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏢 <span>Intranet</span> Corporate</h1>
            <span class="badge">Projet IGA - MidPoint</span>
        </header>
        
        <?php if (isset($db_error)): ?>
            <div class="error">
                <strong>⚠️ Erreur de connexion à la base de données</strong><br>
                <?= htmlspecialchars($db_error) ?>
            </div>
        <?php endif; ?>
        
        <?php if (isset($query_error)): ?>
            <div class="error">
                <strong>⚠️ Erreur de requête</strong><br>
                <?= htmlspecialchars($query_error) ?>
            </div>
        <?php endif; ?>
        
        <div class="stats-grid">
            <div class="stat-card primary">
                <h3>Utilisateurs totaux</h3>
                <div class="value"><?= $stats['total_users'] ?? '0' ?></div>
            </div>
            <div class="stat-card success">
                <h3>Utilisateurs actifs</h3>
                <div class="value"><?= $stats['active_users'] ?? '0' ?></div>
            </div>
            <div class="stat-card warning">
                <h3>Rôles définis</h3>
                <div class="value"><?= $stats['total_roles'] ?? '0' ?></div>
            </div>
        </div>
        
        <div class="main-grid">
            <div class="card">
                <h2>👥 Liste des utilisateurs</h2>
                <?php if (!empty($users)): ?>
                    <table>
                        <thead>
                            <tr>
                                <th>Nom complet</th>
                                <th>Email</th>
                                <th>Département</th>
                                <th>Rôles</th>
                                <th>Statut</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($users as $user): ?>
                                <tr>
                                    <td><strong><?= htmlspecialchars($user['full_name'] ?: $user['username']) ?></strong></td>
                                    <td><?= htmlspecialchars($user['email']) ?></td>
                                    <td><?= htmlspecialchars($user['department'] ?: '-') ?></td>
                                    <td>
                                        <?php 
                                        $roles = $user['roles'] ? explode(', ', $user['roles']) : ['USER'];
                                        foreach ($roles as $role): 
                                            $isSpecial = in_array($role, ['AGENT_COMMERCIAL', 'RH_MANAGER', 'IT_ADMIN', 'MANAGER']);
                                        ?>
                                            <span class="role-tag <?= $isSpecial ? 'special' : '' ?>"><?= htmlspecialchars($role) ?></span>
                                        <?php endforeach; ?>
                                    </td>
                                    <td>
                                        <span class="status-badge <?= $user['enabled'] ? 'active' : 'inactive' ?>">
                                            <?= $user['enabled'] ? 'Actif' : 'Inactif' ?>
                                        </span>
                                    </td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                <?php else: ?>
                    <p style="text-align: center; color: var(--gray-700); padding: 40px;">
                        Aucun utilisateur provisionné.<br>
                        <small>Les utilisateurs seront créés automatiquement par MidPoint.</small>
                    </p>
                <?php endif; ?>
                
                <div class="info-box">
                    <strong>ℹ️ Provisionnement automatique</strong>
                    Les utilisateurs de cette application sont gérés via MidPoint IAM.
                    Les modifications sont propagées automatiquement depuis le référentiel central d'identités.
                </div>
            </div>
            
            <div class="card">
                <h2>📊 Par département</h2>
                <?php if (!empty($stats['by_department'])): ?>
                    <ul class="dept-list">
                        <?php foreach ($stats['by_department'] as $dept): ?>
                            <li>
                                <span><?= htmlspecialchars($dept['department'] ?: 'Non défini') ?></span>
                                <span class="dept-count"><?= $dept['count'] ?></span>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                <?php else: ?>
                    <p style="text-align: center; color: var(--gray-700); padding: 20px;">
                        Aucune donnée
                    </p>
                <?php endif; ?>
            </div>
        </div>
        
        <footer>
            Application Intranet Corporate • Projet IGA BUT3 Informatique • Provisionnement via MidPoint
        </footer>
    </div>
</body>
</html>








