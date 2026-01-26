<?php
/**
 * API REST pour le provisionnement des utilisateurs Intranet
 * Endpoint utilisé par MidPoint pour créer/modifier/supprimer les utilisateurs
 * 
 * Méthodes supportées:
 * - GET /api.php?action=list : Liste tous les utilisateurs
 * - GET /api.php?action=get&username=xxx : Récupère un utilisateur
 * - POST /api.php?action=create : Crée un utilisateur
 * - PUT /api.php?action=update&username=xxx : Met à jour un utilisateur
 * - DELETE /api.php?action=delete&username=xxx : Supprime un utilisateur
 */

header('Content-Type: application/json');

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
    http_response_code(500);
    echo json_encode(['error' => 'Database connection failed', 'message' => $e->getMessage()]);
    exit;
}

$method = $_SERVER['REQUEST_METHOD'];
$action = $_GET['action'] ?? '';

// Récupérer les données JSON pour POST/PUT
$input = [];
if (in_array($method, ['POST', 'PUT'])) {
    $rawInput = file_get_contents('php://input');
    $input = json_decode($rawInput, true) ?: [];
}

try {
    switch ($action) {
        case 'list':
            // Liste tous les utilisateurs
            $stmt = $pdo->query("SELECT * FROM v_users_with_roles ORDER BY username");
            $users = $stmt->fetchAll(PDO::FETCH_ASSOC);
            echo json_encode(['success' => true, 'count' => count($users), 'users' => $users]);
            break;
            
        case 'get':
            // Récupère un utilisateur par username
            $username = $_GET['username'] ?? '';
            if (empty($username)) {
                http_response_code(400);
                echo json_encode(['error' => 'Username required']);
                exit;
            }
            
            $stmt = $pdo->prepare("SELECT * FROM v_users_with_roles WHERE username = ?");
            $stmt->execute([$username]);
            $user = $stmt->fetch(PDO::FETCH_ASSOC);
            
            if ($user) {
                echo json_encode(['success' => true, 'user' => $user]);
            } else {
                http_response_code(404);
                echo json_encode(['error' => 'User not found']);
            }
            break;
            
        case 'create':
        case 'update':
            // Crée ou met à jour un utilisateur (upsert)
            $required = ['username', 'email'];
            foreach ($required as $field) {
                if (empty($input[$field])) {
                    http_response_code(400);
                    echo json_encode(['error' => "Field '$field' is required"]);
                    exit;
                }
            }
            
            // Upsert utilisateur
            $stmt = $pdo->prepare("SELECT upsert_user(?, ?, ?, ?, ?, ?, ?, ?)");
            $stmt->execute([
                $input['username'],
                $input['email'],
                $input['first_name'] ?? null,
                $input['last_name'] ?? null,
                $input['department'] ?? null,
                $input['title'] ?? null,
                $input['employee_number'] ?? null,
                isset($input['enabled']) ? ($input['enabled'] ? true : false) : true
            ]);
            $userId = $stmt->fetchColumn();
            
            // Gérer les rôles si fournis
            if (!empty($input['roles'])) {
                // D'abord supprimer tous les rôles existants
                $stmt = $pdo->prepare("DELETE FROM user_roles WHERE user_id = ?");
                $stmt->execute([$userId]);
                
                // Puis assigner les nouveaux rôles
                $roles = is_array($input['roles']) ? $input['roles'] : explode(',', $input['roles']);
                foreach ($roles as $role) {
                    $role = trim($role);
                    if (!empty($role)) {
                        $stmt = $pdo->prepare("SELECT assign_role(?, ?)");
                        $stmt->execute([$input['username'], $role]);
                    }
                }
            }
            
            echo json_encode([
                'success' => true, 
                'message' => $action === 'create' ? 'User created' : 'User updated',
                'user_id' => $userId
            ]);
            break;
            
        case 'delete':
            // Supprime un utilisateur
            $username = $_GET['username'] ?? $input['username'] ?? '';
            if (empty($username)) {
                http_response_code(400);
                echo json_encode(['error' => 'Username required']);
                exit;
            }
            
            $stmt = $pdo->prepare("DELETE FROM app_users WHERE username = ?");
            $stmt->execute([$username]);
            
            if ($stmt->rowCount() > 0) {
                echo json_encode(['success' => true, 'message' => 'User deleted']);
            } else {
                http_response_code(404);
                echo json_encode(['error' => 'User not found']);
            }
            break;
            
        case 'assign_role':
            // Assigne un rôle à un utilisateur
            $username = $input['username'] ?? '';
            $role = $input['role'] ?? '';
            
            if (empty($username) || empty($role)) {
                http_response_code(400);
                echo json_encode(['error' => 'Username and role required']);
                exit;
            }
            
            $stmt = $pdo->prepare("SELECT assign_role(?, ?)");
            $stmt->execute([$username, $role]);
            echo json_encode(['success' => true, 'message' => "Role '$role' assigned to '$username'"]);
            break;
            
        case 'revoke_role':
            // Révoque un rôle d'un utilisateur
            $username = $input['username'] ?? '';
            $role = $input['role'] ?? '';
            
            if (empty($username) || empty($role)) {
                http_response_code(400);
                echo json_encode(['error' => 'Username and role required']);
                exit;
            }
            
            $stmt = $pdo->prepare("SELECT revoke_role(?, ?)");
            $stmt->execute([$username, $role]);
            echo json_encode(['success' => true, 'message' => "Role '$role' revoked from '$username'"]);
            break;
            
        case 'health':
            // Health check
            echo json_encode([
                'success' => true, 
                'status' => 'healthy',
                'database' => 'connected',
                'timestamp' => date('c')
            ]);
            break;
            
        default:
            http_response_code(400);
            echo json_encode([
                'error' => 'Invalid action',
                'available_actions' => ['list', 'get', 'create', 'update', 'delete', 'assign_role', 'revoke_role', 'health']
            ]);
    }
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => 'Database error', 'message' => $e->getMessage()]);
}








