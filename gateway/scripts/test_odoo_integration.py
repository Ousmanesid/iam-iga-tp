#!/usr/bin/env python3
"""
Script de test de l'intégration Odoo ↔ Aegis Gateway

Usage:
    python scripts/test_odoo_integration.py
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001/api/v1"

def print_section(title):
    """Affiche un titre de section."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def test_sync_status():
    """Test 1: Vérifier le statut de synchronisation."""
    print_section("TEST 1: Statut de synchronisation Odoo")
    
    response = requests.get(f"{BASE_URL}/odoo/sync/status")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"📊 Résultat:")
        print(f"   • Odoo connecté: {data['odoo_connected']}")
        print(f"   • Users depuis Odoo: {data['local_users_from_odoo']}")
        print(f"   • Dernière vérification: {data['last_check']}")
        return data['odoo_connected']
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(f"   {response.text}")
        return False

def test_get_employees():
    """Test 2: Récupérer les employés depuis Odoo."""
    print_section("TEST 2: Récupération des employés Odoo")
    
    response = requests.get(f"{BASE_URL}/odoo/employees")
    
    if response.status_code == 200:
        employees = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"📊 {len(employees)} employés trouvés:")
        
        for i, emp in enumerate(employees[:5], 1):  # Afficher les 5 premiers
            print(f"\n   {i}. {emp.get('givenName')} {emp.get('familyName')}")
            print(f"      Email: {emp.get('email')}")
            print(f"      Poste: {emp.get('title')}")
            print(f"      Département: {emp.get('department')}")
        
        if len(employees) > 5:
            print(f"\n   ... et {len(employees) - 5} autres")
        
        return len(employees) > 0
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(f"   {response.text}")
        return False

def test_sync():
    """Test 3: Lancer la synchronisation."""
    print_section("TEST 3: Synchronisation Odoo → Aegis")
    
    print("🔄 Lancement de la synchronisation...")
    response = requests.post(f"{BASE_URL}/odoo/sync")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Status: {response.status_code}")
        print(f"📊 Résultat:")
        print(f"   • Succès: {data.get('success')}")
        print(f"   • Message: {data.get('message')}")
        
        if 'stats' in data:
            stats = data['stats']
            print(f"   • Total: {stats.get('total', 0)}")
            print(f"   • Créés: {stats.get('created', 0)}")
            print(f"   • Mis à jour: {stats.get('updated', 0)}")
            print(f"   • Ignorés: {stats.get('skipped', 0)}")
            
            if stats.get('errors'):
                print(f"   • Erreurs: {len(stats['errors'])}")
                for err in stats['errors'][:3]:
                    print(f"      - {err}")
        
        return data.get('success', False)
    else:
        print(f"❌ Erreur: {response.status_code}")
        error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
        print(f"   {error_data.get('detail', response.text)}")
        return False

def test_verify_users():
    """Test 4: Vérifier les utilisateurs synchronisés."""
    print_section("TEST 4: Vérification des utilisateurs dans Aegis")
    
    response = requests.get(f"{BASE_URL}/users")
    
    if response.status_code == 200:
        users = response.json()
        odoo_users = [u for u in users if u.get('source') == 'odoo_sync']
        
        print(f"✅ Status: {response.status_code}")
        print(f"📊 Utilisateurs:")
        print(f"   • Total: {len(users)}")
        print(f"   • Depuis Odoo: {len(odoo_users)}")
        
        if odoo_users:
            print(f"\n   Exemples d'utilisateurs Odoo:")
            for i, user in enumerate(odoo_users[:3], 1):
                print(f"\n   {i}. {user.get('first_name')} {user.get('last_name')}")
                print(f"      Email: {user.get('email')}")
                print(f"      Poste: {user.get('job_title')}")
                print(f"      Rôle: {user.get('role')}")
                print(f"      Source: {user.get('source')} ✨")
        
        return len(odoo_users) > 0
    else:
        print(f"❌ Erreur: {response.status_code}")
        print(f"   {response.text}")
        return False

def test_dashboard_access():
    """Test 5: Vérifier l'accès au dashboard."""
    print_section("TEST 5: Accès au Dashboard")
    
    dashboard_url = "http://localhost:5174"
    
    try:
        response = requests.get(dashboard_url, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Dashboard accessible à {dashboard_url}")
            print(f"📊 Le dashboard affiche les utilisateurs synchronisés depuis Odoo")
            print(f"\n   🌐 Ouvrez dans votre navigateur:")
            print(f"   → {dashboard_url}")
            return True
        else:
            print(f"⚠️  Dashboard status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Dashboard non accessible: {e}")
        return False

def main():
    """Exécute tous les tests."""
    print("\n" + "="*70)
    print("  🧪 TEST DE L'INTÉGRATION ODOO ↔ AEGIS GATEWAY")
    print("="*70)
    print(f"\n⏰ Démarré à: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Test 1: Status
    results['status'] = test_sync_status()
    
    if not results['status']:
        print("\n" + "="*70)
        print("⚠️  ODOO NON CONNECTÉ")
        print("="*70)
        print("\n💡 Pour démarrer Odoo:")
        print("   cd /srv/projet/iam-iga-tp")
        print("   docker-compose up -d odoo")
        print("\n   Puis relancer ce script.")
        return
    
    # Test 2: Get Employees
    results['get_employees'] = test_get_employees()
    
    # Test 3: Sync
    if results['get_employees']:
        results['sync'] = test_sync()
    else:
        print("\n⚠️  Aucun employé dans Odoo, synchronisation ignorée")
        results['sync'] = False
    
    # Test 4: Verify Users
    results['verify'] = test_verify_users()
    
    # Test 5: Dashboard
    results['dashboard'] = test_dashboard_access()
    
    # Résumé final
    print("\n" + "="*70)
    print("  📊 RÉSUMÉ DES TESTS")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"{icon} {test_name.replace('_', ' ').title()}: {'PASS' if result else 'FAIL'}")
    
    print(f"\n🎯 Score: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
        print("   L'intégration Odoo ↔ Aegis Gateway fonctionne correctement.")
    elif passed > 0:
        print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("   Vérifiez la configuration et les logs.")
    else:
        print("\n❌ TOUS LES TESTS ONT ÉCHOUÉ")
        print("   Vérifiez que les services sont démarrés.")
    
    print("\n" + "="*70)
    print(f"⏰ Terminé à: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
