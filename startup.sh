#!/bin/bash

set -e

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Démarrage du système..."
echo ""

docker compose up -d --build

sleep 20

echo ""
echo "✅ Services démarrés !"
echo ""
echo "📊 URLs d'accès :"
echo "   • Airflow      : http://localhost:8088 (admin/admin)"
echo "   • API          : http://localhost:8000"
echo "   • Dashboard    : http://localhost:8501"
echo ""
echo "🎯 Prochaines étapes :"
echo "   1. Ouvrir http://localhost:8088"
echo "   2. Cliquer sur recommendation_pipeline → Trigger DAG"
echo "   3. Attendre ~10 min"
echo ""

