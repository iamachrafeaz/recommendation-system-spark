#!/bin/bash
# clean.sh - Nettoyage rapide du projet

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🧹 Nettoyage du projet..."
echo ""

# 1. Arrêter et nettoyer Docker
echo "1️⃣  Docker cleanup..."
cd "$SCRIPT_DIR"
docker compose down -v 2>/dev/null || true
echo "   ✅ Volumes supprimés"

# 2. Supprimer tous les .md sauf README.md
echo ""
echo "2️⃣  Supprimer fichiers de documentation..."
find "$SCRIPT_DIR" -maxdepth 1 -type f -name "*.md" ! -name "README.md" -delete 2>/dev/null || true
echo "   ✅ Docs supprimées (sauf README.md)"

# 3. Supprimer __pycache__
echo ""
echo "3️⃣  Supprimer caches Python..."
find "$SCRIPT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$SCRIPT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
echo "   ✅ Caches supprimés"

# 4. Supprimer spark/output/*
echo ""
echo "4️⃣  Supprimer modèles Spark..."
rm -rf "$SCRIPT_DIR/spark/output"/* 2>/dev/null || true
echo "   ✅ Modèles supprimés"

# 5. Nettoyer logs et données temporaires
echo ""
echo "5️⃣  Supprimer fichiers temporaires..."
rm -rf "$SCRIPT_DIR/airflow/logs" 2>/dev/null || true
rm -rf /tmp/checkpoints 2>/dev/null || true
rm -rf /tmp/streaming.log 2>/dev/null || true
echo "   ✅ Fichiers temporaires supprimés"

echo ""
echo "✅ Nettoyage terminé !"
echo ""
echo "Prêt à redémarrer :"
echo "  $ ./startup.sh"

