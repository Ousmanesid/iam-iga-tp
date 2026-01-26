#!/usr/bin/env python3
"""
Script d'épuration des données RH exportées depuis Odoo
Conserve uniquement les colonnes nécessaires pour MidPoint
"""

import csv
import sys
from pathlib import Path

# Colonnes à conserver pour MidPoint
IDENTIFIER_FIELD = 'personalNumber'
IDENTIFIER_ALIASES = ('personalNumber', 'employeeNumber')
REQUIRED_COLUMNS = [
    IDENTIFIER_FIELD,
    'givenName',
    'familyName',
    'email',
    'department',
    'title',
    'status'
]

def clean_hr_csv(input_file: Path, output_file: Path) -> None:
    """
    Nettoie le fichier CSV RH en conservant uniquement les colonnes nécessaires
    
    Args:
        input_file: Chemin du fichier CSV brut
        output_file: Chemin du fichier CSV nettoyé
    """
    print(f"📖 Lecture du fichier: {input_file}")
    
    if not input_file.exists():
        print(f"❌ Erreur: Le fichier {input_file} n'existe pas")
        sys.exit(1)
    
    # Lecture du CSV brut
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        raw_data = list(reader)
        raw_columns = reader.fieldnames
    
    print(f"✅ {len(raw_data)} lignes lues")
    print(f"📋 Colonnes originales: {', '.join(raw_columns)}")
    
    # Vérification de la présence des colonnes requises
    base_columns = [col for col in REQUIRED_COLUMNS if col != IDENTIFIER_FIELD]
    missing_columns = [col for col in base_columns if col not in raw_columns]
    identifier_present = any(alias in raw_columns for alias in IDENTIFIER_ALIASES)
    
    if missing_columns or not identifier_present:
        detail = []
        if missing_columns:
            detail.append(f"Colonnes manquantes: {', '.join(missing_columns)}")
        if not identifier_present:
            detail.append(f"Aucune colonne identifiant détectée ({', '.join(IDENTIFIER_ALIASES)})")
        print(f"❌ {' | '.join(detail)}")
        sys.exit(1)
    
    # Filtrage et nettoyage des données
    cleaned_data = []
    for row in raw_data:
        cleaned_row = {}
        identifier_value = ''
        for alias in IDENTIFIER_ALIASES:
            identifier_value = row.get(alias, '').strip()
            if identifier_value:
                break
        cleaned_row[IDENTIFIER_FIELD] = identifier_value
        
        for col in base_columns:
            cleaned_row[col] = row.get(col, '').strip()
        
        # Ne conserver que les lignes avec un numéro d'employé valide
        if cleaned_row[IDENTIFIER_FIELD]:
            cleaned_data.append(cleaned_row)
    
    print(f"🧹 {len(cleaned_data)} lignes valides après nettoyage")
    print(f"📋 Colonnes conservées: {', '.join(REQUIRED_COLUMNS)}")
    
    # Écriture du CSV nettoyé
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(cleaned_data)
    
    print(f"✅ Fichier nettoyé créé: {output_file}")
    print("")
    print("📊 Statistiques par département:")
    
    # Statistiques
    dept_counts = {}
    status_counts = {}
    
    for row in cleaned_data:
        dept = row['department']
        status = row['status']
        dept_counts[dept] = dept_counts.get(dept, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for dept, count in sorted(dept_counts.items()):
        print(f"   - {dept}: {count} employé(s)")
    
    print("")
    print("📊 Statistiques par statut:")
    for status, count in sorted(status_counts.items()):
        print(f"   - {status}: {count} employé(s)")


def main():
    """Point d'entrée principal"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    input_file = project_root / 'data' / 'hr' / 'hr_raw.csv'
    output_file = project_root / 'data' / 'hr' / 'hr_clean.csv'
    
    print("🧪 Script de nettoyage des données RH")
    print("=" * 60)
    print("")
    
    clean_hr_csv(input_file, output_file)
    
    print("")
    print("=" * 60)
    print("✅ Nettoyage terminé avec succès")
    print(f"📁 Fichier de sortie: {output_file}")


if __name__ == '__main__':
    main()

