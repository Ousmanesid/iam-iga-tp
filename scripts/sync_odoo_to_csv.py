#!/usr/bin/env python3
"""
Script complet : Export Odoo → CSV → Copie dans MidPoint
Usage: python3 sync_odoo_to_csv.py
"""
import csv
import subprocess

def export_from_odoo():
    """Exporter depuis Odoo via le script bash"""
    print("=" * 70)
    print("🚀 SYNCHRONISATION ODOO → MIDPOINT CSV")
    print("=" * 70)
    print("\n📥 Étape 1/3: Export depuis Odoo...")
    
    cmd = ["bash", "/srv/projet/iam-iga-tp/scripts/odoo_hr_export.sh", "--docker"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Erreur lors de l'export Odoo:")
        print(result.stderr)
        return False
    
    print(result.stdout)
    return True

def copy_to_midpoint():
    """Copier le CSV dans MidPoint"""
    print("\n📤 Étape 2/3: Copie dans MidPoint...")
    
    cmd = [
        "docker", "exec", "midpoint",
        "cp", "/data/hr/hr_clean.csv", "/opt/midpoint-data/hr/hr_clean.csv"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Erreur lors de la copie:")
        print(result.stderr)
        return False
    
    print("✅ Fichier copié dans /opt/midpoint-data/hr/hr_clean.csv")
    return True

def verify():
    """Vérifier le résultat"""
    print("\n✅ Étape 3/3: Vérification...")
    
    # Compter les lignes
    cmd = ["docker", "exec", "midpoint", "wc", "-l", "/opt/midpoint-data/hr/hr_clean.csv"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        count = result.stdout.split()[0]
        employee_count = int(count) - 1  # -1 pour l'en-tête
        print(f"📊 {employee_count} employés dans le CSV MidPoint")
    
    # Afficher les dernières lignes
    print("\n📋 Derniers employés:")
    cmd = ["docker", "exec", "midpoint", "tail", "-5", "/opt/midpoint-data/hr/hr_clean.csv"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)

def main():
    # Étape 1: Export Odoo
    if not export_from_odoo():
        print("\n❌ Échec de l'export Odoo")
        return
    
    # Étape 2: Copie dans MidPoint
    if not copy_to_midpoint():
        print("\n❌ Échec de la copie dans MidPoint")
        return
    
    # Étape 3: Vérification
    verify()
    
    # Instructions finales
    print("\n" + "=" * 70)
    print("✅ SYNCHRONISATION TERMINÉE !")
    print("=" * 70)
    print("\n📝 Prochaine étape:")
    print("   1. Allez sur http://localhost:8080/midpoint")
    print("   2. Resources → HR CSV Source")
    print("   3. Cliquez sur 'Import from resource'")
    print("\n💡 Ou attendez que la task automatique importe (si active)")
    print("=" * 70)

if __name__ == '__main__':
    main()
