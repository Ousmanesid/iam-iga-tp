#!/bin/bash
#
# Script de synchronisation complète
# Odoo → CSV → MidPoint → Toutes les cibles
#

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║      🔄 SYNCHRONISATION COMPLÈTE IGA                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

cd /root/iam-iga-tp

# Étape 1: Export Odoo → CSV
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 Étape 1: Export Odoo → CSV"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 scripts/export_odoo_hr.py
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de l'export Odoo"
    exit 1
fi

# Étape 2: Synchronisation vers Intranet PostgreSQL
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏢 Étape 2: Provisionnement Intranet (PostgreSQL)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 scripts/provision_intranet.py --action sync --csv data/hr/hr_clean.csv
if [ $? -ne 0 ]; then
    echo "⚠️  Avertissement: erreurs lors du provisionnement Intranet"
fi

# Résumé
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║      ✅ SYNCHRONISATION TERMINÉE                           ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  Les données ont été synchronisées:                        ║"
echo "║    • Odoo → CSV (hr_clean.csv)                             ║"
echo "║    • CSV → Intranet PostgreSQL                             ║"
echo "║                                                            ║"
echo "║  Pour MidPoint:                                            ║"
echo "║    → L'import automatique synchronisera les identités      ║"
echo "║    → Ou lancez manuellement la tâche 'HR CSV Import'       ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""








