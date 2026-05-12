import os
import time

import requests
import streamlit as st

# ── Config page ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RecoSys · Live Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── CSS personnalisé ──────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Sora:wght@300;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Sora', sans-serif;
        background-color: #0d0f1a;
        color: #e2e8f0;
    }

    .stApp { background-color: #0d0f1a; }
    
    header {
        background-color: #0d0f1a !important;
        color: #e2e8f0;
    }
    
    /* Header */
    .dash-header {
        padding: 1.5rem 0 1rem 0;
        border-bottom: 1px solid #1e2a45;
        margin-bottom: 1.5rem;
    }
    .dash-title {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
        margin: 0;
    }
    .dash-subtitle {
        color: #64748b;
        font-size: 0.85rem;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 0.25rem;
    }

    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #131929, #1a2235);
        border: 1px solid #1e2d45;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
        transition: border-color .2s;
    }
    .kpi-card:hover { border-color: #38bdf8; }
    .kpi-label {
        font-size: 0.72rem;
        font-family: 'JetBrains Mono', monospace;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.4rem;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #38bdf8;
        line-height: 1;
    }
    .kpi-sub { font-size: 0.72rem; color: #334155; margin-top: 0.3rem; }

    /* Rec table */
    .rec-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    .rec-table th {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #475569;
        padding: 0.6rem 1rem;
        text-align: left;
        border-bottom: 1px solid #1e2d45;
    }
    .rec-table td {
        padding: 0.75rem 1rem;
        font-size: 0.9rem;
        border-bottom: 1px solid #131929;
        vertical-align: middle;
    }
    .rec-table tr:hover td { background: #131929; }
    .rank-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px; height: 28px;
        border-radius: 50%;
        background: #1e2d45;
        color: #38bdf8;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .rank-badge.gold   { background: #78350f; color: #fbbf24; }
    .rank-badge.silver { background: #1e293b; color: #94a3b8; }
    .rank-badge.bronze { background: #431407; color: #f97316; }

    .product-id {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #e2e8f0;
    }
    .category-tag {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
        background: #0f2942;
        color: #38bdf8;
        border: 1px solid #164e80;
    }

    /* Section titles */
    .section-title {
        font-size: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #475569;
        margin: 1.5rem 0 0.75rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-title::after {
        content: '';
        flex: 1;
        height: 1px;
        background: #1e2d45;
    }

    /* Live feed */
    .feed-item {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid #131929;
        font-size: 0.78rem;
    }
    .feed-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #22d3ee;
        box-shadow: 0 0 6px #22d3ee;
        flex-shrink: 0;
    }
    .feed-user { color: #818cf8; font-family: 'JetBrains Mono', monospace; }
    .feed-time { color: #334155; margin-left: auto; font-size: 0.7rem; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0a0d17 !important;
        border-right: 1px solid #1e2a45;
    }
    [data-testid="stSidebar"] * { color: #94a3b8; }

    /* Selectbox & button */
    .stSelectbox > div > div { background: #131929 !important; border-color: #1e2d45 !important; }
    .stButton > button {
        background: linear-gradient(135deg, #0369a1, #4f46e5) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
        padding: 0.5rem 1.5rem !important;
        transition: opacity .2s !important;
    }
    .stButton > button:hover { opacity: 0.85 !important; }

    /* Status pill */
    .status-pill {
        display: inline-flex; align-items: center; gap: 0.4rem;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.72rem;
        font-family: 'JetBrains Mono', monospace;
        background: #052e16;
        color: #4ade80;
        border: 1px solid #14532d;
    }
    .status-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: #4ade80;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }

    /* Hide default streamlit chrome */
    #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

CATEGORY_MAP = {
    "B000": ("☕ Coffee & Tea", "#0f2942"),
    "B001": ("🍫 Chocolate & Candy", "#2d1b0e"),
    "B002": ("🥜 Nuts & Snacks", "#1a1a0a"),
    "B003": ("🥣 Cereal & Breakfast", "#0e1f2d"),
    "B004": ("🍵 Herbal & Wellness", "#0d2219"),
    "B005": ("🌶️ Spices & Sauces", "#2d0a0a"),
    "B006": ("🧴 Oils & Condiments", "#1f1a08"),
    "B007": ("🥤 Beverages", "#0a1f2d"),
    "B008": ("🍪 Biscuits & Cookies", "#2d1908"),
    "B009": ("🥫 Canned & Preserved", "#0d0d2d"),
}

def get_category(product_id: str) -> tuple:
    prefix = product_id[:4].upper()
    return CATEGORY_MAP.get(prefix, ("🛒 Food & Grocery", "#131929"))


def format_time_ago(iso_str: str) -> str:
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = int((datetime.now(timezone.utc) - dt).total_seconds())
        if delta < 60:
            return f"{delta}s ago"
        if delta < 3600:
            return f"{delta//60}m ago"
        return f"{delta//3600}h ago"
    except Exception:
        return ""


@st.cache_data(ttl=30)
def fetch_users():
    try:
        r = requests.get(f"{API_BASE_URL}/processed_users", timeout=5)
        if r.ok:
            return r.json().get("user_ids", [])
    except Exception:
        pass
    return []


@st.cache_data(ttl=10)
def fetch_metrics():
    try:
        r = requests.get(f"{API_BASE_URL}/metrics/stream", timeout=5)
        return r.json() if r.ok else {}
    except Exception:
        return {}


@st.cache_data(ttl=10)
def fetch_activity():
    try:
        r = requests.get(f"{API_BASE_URL}/recent_activity", timeout=5)
        return r.json().get("activity", []) if r.ok else []
    except Exception:
        return []


# ── Sidebar : Live Feed ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-family:JetBrains Mono,monospace;font-size:0.7rem;"
        "text-transform:uppercase;letter-spacing:2px;color:#475569;"
        "margin-bottom:1rem'>⚡ Live Feed</div>",
        unsafe_allow_html=True,
    )

    activity = fetch_activity()
    if activity:
        for item in activity[:15]:
            uid = item.get("user_id", "")
            t = format_time_ago(item.get("updated_at", ""))
            n = item.get("nb_recs", 0)
            st.markdown(
                f"""<div class="feed-item">
                    <div class="feed-dot"></div>
                    <span class="feed-user">{uid[:14]}…</span>
                    <span style="color:#334155;font-size:0.7rem">{n} recs</span>
                    <span class="feed-time">{t}</span>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div style='color:#334155;font-size:0.8rem;font-family:JetBrains Mono,monospace'>"
            "En attente de données...</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    """<div class="dash-header">
        <div style="display:flex;align-items:center;justify-content:space-between">
            <div>
                <p class="dash-title">RecoSys Dashboard</p>
                <p class="dash-subtitle">Amazon Fine Food Reviews · ALS Collaborative Filtering · Spark Streaming</p>
            </div>
            <div class="status-pill">
                <div class="status-dot"></div>LIVE
            </div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

# ── KPI row ───────────────────────────────────────────────────────────────────
metrics = fetch_metrics()
users_list = fetch_users()

total_rows = metrics.get("total_rows_seen", "—")
total_users = len(users_list)   # Vrai compteur depuis les clés Redis
last_batch = metrics.get("last_batch_id", "—")
last_ts = metrics.get("last_batch_ts", "")
last_ts_fmt = format_time_ago(last_ts) if last_ts else "—"
last_rows = metrics.get("last_input_rows", "—")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Rows vus (total)</div>
            <div class="kpi-value">{total_rows}</div>
            <div class="kpi-sub">événements Kafka traités</div>
        </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Users avec recs</div>
            <div class="kpi-value" style="color:#818cf8">{total_users}</div>
            <div class="kpi-sub">clés recs:user:* dans Redis</div>
        </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Dernier batch</div>
            <div class="kpi-value" style="color:#34d399">#{last_batch}</div>
            <div class="kpi-sub">{last_ts_fmt}</div>
        </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-label">Rows dernier batch</div>
            <div class="kpi-value" style="color:#fb923c">{last_rows}</div>
            <div class="kpi-sub">messages dans ce micro-batch</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Recherche utilisateur ─────────────────────────────────────────────────────
st.markdown(
    '<div class="section-title">🔍 Recherche de recommandations</div>',
    unsafe_allow_html=True,
)

col_sel, col_btn = st.columns([4, 1])
with col_sel:
    if users_list:
        selected_user = st.selectbox(
            "Sélectionner un utilisateur",
            options=[""] + users_list,
            format_func=lambda x: "— Choisir un user_id —" if x == "" else x,
            label_visibility="collapsed",
        )
    else:
        selected_user = st.text_input(
            "user_id",
            placeholder="Aucun user chargé — saisir manuellement",
            label_visibility="collapsed",
        )

with col_btn:
    search_clicked = st.button("SEARCH →", use_container_width=True)

# ── Résultats ─────────────────────────────────────────────────────────────────
if search_clicked and selected_user:
    try:
        resp = requests.get(
            f"{API_BASE_URL}/recommendations/{selected_user.strip()}",
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            recs = data.get("product_ids", [])[:5]
            updated = format_time_ago(data.get("updated_at", ""))

            st.markdown(
                f"""<div style="margin:1rem 0 0.5rem;display:flex;
                    align-items:center;gap:1rem">
                    <span style="font-family:'JetBrains Mono',monospace;
                    font-size:0.85rem;color:#818cf8">{selected_user}</span>
                    <span style="font-size:0.72rem;color:#334155">
                    mise à jour {updated}</span>
                </div>""",
                unsafe_allow_html=True,
            )

            rank_classes = ["gold", "silver", "bronze", "", ""]
            rows_html = ""
            for i, pid in enumerate(recs):
                cat_label, cat_bg = get_category(pid)
                rank_cls = rank_classes[i]
                rows_html += f"""
                <tr>
                    <td><span class="rank-badge {rank_cls}">{i+1}</span></td>
                    <td><span class="product-id">{pid}</span></td>
                    <td><span class="category-tag" style="background:{cat_bg}">{cat_label}</span></td>
                    <td>
                        <div style="background:#0f172a;border-radius:4px;
                        height:6px;width:100%;max-width:120px">
                            <div style="background:linear-gradient(90deg,#38bdf8,#818cf8);
                            border-radius:4px;height:6px;
                            width:{100 - i*15}%"></div>
                        </div>
                    </td>
                </tr>"""

            st.markdown(
                f"""<table class="rec-table">
                    <thead><tr>
                        <th>#</th>
                        <th>Product ID</th>
                        <th>Catégorie (estimée)</th>
                        <th>Score ALS</th>
                    </tr></thead>
                    <tbody>{rows_html}</tbody>
                </table>""",
                unsafe_allow_html=True,
            )

        elif resp.status_code == 404:
            st.markdown(
                f"""<div style="padding:1.5rem;background:#0f1720;border:1px solid #1e2d45;
                border-radius:10px;color:#475569;font-family:'JetBrains Mono',monospace;
                font-size:0.85rem;margin-top:1rem">
                ⚠️ Aucune recommandation trouvée pour <span style="color:#818cf8">
                {selected_user}</span></div>""",
                unsafe_allow_html=True,
            )
        else:
            st.error(f"Erreur API : statut {resp.status_code}")

    except requests.RequestException as exc:
        st.error(f"Impossible de contacter l'API : {exc}")

elif search_clicked and not selected_user:
    st.warning("Veuillez sélectionner ou saisir un user_id.")