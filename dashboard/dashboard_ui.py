import os

import requests
import streamlit as st

st.set_page_config(page_title="Recommandations Produits", layout="centered")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.title("Dashboard Recommandation (Amazon Fine Food Reviews)")

user_id = st.text_input(
	"Rechercher un user_id",
	value="",
	placeholder="Ex: A3SGXH7AUHU8GW",
)

if st.button("Afficher Top-5"):
	clean_user_id = user_id.strip()
	if not clean_user_id:
		st.warning("Merci de saisir un user_id.")
	else:
		try:
			response = requests.get(
				f"{API_BASE_URL}/recommendations/{clean_user_id}",
				timeout=5,
			)
			if response.status_code == 200:
				data = response.json()
				st.subheader(f"Top recommandations pour user_id={data.get('user_id')}")
				recommendations = data.get("product_ids", [])
				if recommendations:
					for index, product_id in enumerate(recommendations[:5], start=1):
						st.write(f"{index}. {product_id}")
				else:
					st.info("Aucun produit recommande pour cet utilisateur.")
			elif response.status_code == 404:
				st.info("Aucune recommandation trouvee pour cet utilisateur.")
			else:
				st.error(f"Erreur API: statut {response.status_code}")
		except requests.RequestException as exc:
			st.error(f"Impossible de contacter l'API: {exc}")

st.divider()
st.subheader("Metriques flux Kafka")

try:
	metrics_response = requests.get(f"{API_BASE_URL}/metrics/stream", timeout=5)
	metrics = metrics_response.json() if metrics_response.ok else {}

	col1, col2, col3 = st.columns(3)
	col1.metric("Rows vus (total)", metrics.get("total_rows_seen", "0"))
	col2.metric("Users traites (total)", metrics.get("total_users_processed", "0"))
	col3.metric("Dernier batch", metrics.get("last_batch_id", "-"))

	st.caption(f"Dernier timestamp batch: {metrics.get('last_batch_ts', '-')}")
except requests.RequestException as exc:
	st.error(f"Impossible de recuperer les metriques: {exc}")

