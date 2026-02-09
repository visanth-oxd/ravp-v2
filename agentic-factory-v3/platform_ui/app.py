"""
Streamlit UI for RAVP v2 (REgulated Agent Vending Platform).
Manage Tools and Manage Policies tabs are always visible.
Log in as admin@platform.com to use them.
"""

import streamlit as st
import requests
import os
import random
import base64
import textwrap

st.set_page_config(page_title="Regulated Agent Vending Platform", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")
API_BASE_URL = os.getenv("API_URL", "http://localhost:8010")

# Resolve path to logo and cloud icons (works when run from repo root or platform_ui)
_UI_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(_UI_DIR, "assets", "logo.svg")
CLOUD_ICONS_DIR = os.path.join(_UI_DIR, "assets", "cloud")

def _load_cloud_icon_data_uri(names: str | list[str]) -> str | None:
    """Load a cloud icon from assets/cloud/ as a data URI. names: one filename stem or list to try in order (e.g. ['gcp','gke'])."""
    if isinstance(names, str):
        names = [names]
    for name in names:
        for ext in (".svg", ".png"):
            path = os.path.join(CLOUD_ICONS_DIR, name + ext)
            if os.path.isfile(path):
                try:
                    with open(path, "rb") as f:
                        raw = f.read()
                    b64 = base64.b64encode(raw).decode("ascii")
                    mime = "image/svg+xml" if ext == ".svg" else "image/png"
                    return f"data:{mime};base64,{b64}"
                except Exception:
                    pass
    return None

# Custom styling for a cleaner, more intuitive UI
st.markdown("""
<style>
  /* Main content area */
  .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
  /* Platform header in main - larger title */
  .ravp-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(37, 99, 235, 0.2); }
  .ravp-header img { width: 56px; height: 56px; flex-shrink: 0; }
  .ravp-main-title { font-size: 2.25rem !important; font-weight: 700 !important; color: #1e293b !important; margin: 0 !important; letter-spacing: -0.03em !important; line-height: 1.2 !important; }
  .ravp-tagline { font-size: 0.85rem; color: #64748b; margin: 0.25rem 0 0 0; font-weight: 500; letter-spacing: 0.05em; }
  .ravp-platform-tagline { margin: 0.35rem 0 0 0; max-width: 100%; font-size: 1rem; color: #475569; font-weight: 500; line-height: 1.4; }
  .ravp-platform-tagline .ravp-tagline-actions { color: #64748b; }
  .ravp-platform-tagline .ravp-tagline-actions strong { color: #334155; font-weight: 600; }
  .ravp-platform-tagline .ravp-tagline-sep { color: #94a3b8; font-weight: 300; margin: 0 0.15rem; }
  .ravp-cloud-native { font-size: 0.9rem; color: #64748b; font-weight: 600; margin: 0 0 0.5rem 0; text-align: center; letter-spacing: 0.02em; }
  .ravp-cloud-logos { display: flex; flex-wrap: wrap; gap: 0.4rem 0.5rem; justify-content: center; color: #64748b; align-items: center; }
  .ravp-cloud-logos img { width: 28px; height: 28px; object-fit: contain; }
  .ravp-cloud-logos svg { width: 28px; height: 28px; flex-shrink: 0; display: block; }
  .ravp-cloud-logos .ravp-cloud-logo-inline { display: inline-flex; align-items: center; justify-content: center; }
  /* Sidebar agent list */
  .sidebar .agent-list-item { padding: 0.4rem 0; border-radius: 6px; }
  .sidebar [data-testid="stSidebar"] .stButton > button { width: 100%; justify-content: flex-start; text-align: left; }
  /* Sidebar branding */
  .sidebar .ravp-sidebar-brand { text-align: center; padding: 0.5rem 0 1rem 0; border-bottom: 1px solid rgba(0,0,0,0.08); margin-bottom: 1rem; }
  .sidebar .ravp-sidebar-brand img { width: 40px; height: 40px; margin-bottom: 0.5rem; }
  .sidebar .ravp-sidebar-title { font-size: 0.85rem; font-weight: 600; color: #1e293b; margin: 0; line-height: 1.3; }
  .sidebar .ravp-sidebar-tagline { font-size: 0.7rem; color: #64748b; margin: 0.25rem 0 0 0; letter-spacing: 0.06em; }
  /* Tabs and sections */
  stTabs [data-baseweb="tab-list"] { gap: 0.25rem; }
  .stTabs [data-baseweb="tab"] { padding: 0.6rem 1rem; border-radius: 8px; }
  /* Cards and expanders */
  .streamlit-expanderHeader { font-weight: 600; }
  /* Footer */
  .ravp-footer { font-size: 0.75rem; color: #94a3b8; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e2e8f0; }
  /* Landing / first page: dot-grid + robots (full-width black box) */
  .ravp-landing-wrap { position: relative; min-height: 560px; border-radius: 16px; overflow: hidden; margin: 1.5rem 0 2rem 0; display: flex; flex-direction: column; }
  .ravp-landing-bg { position: absolute; inset: 0; background: linear-gradient(180deg, #000000 0%, #0a0f0a 25%, #051005 50%, #000000 75%, #020802 100%); z-index: 0; }
  .ravp-landing-bg::before { content: ""; position: absolute; inset: 0; background-image: radial-gradient(ellipse 80% 50% at 50% 50%, rgba(0, 255, 65, 0.06) 0%, transparent 55%); z-index: 1; }
  .ravp-dots-grid { position: absolute; inset: 0; display: grid; grid-template-columns: repeat(14, 1fr); grid-template-rows: repeat(9, 1fr); z-index: 1; pointer-events: none; padding: 2% 2%; }
  .ravp-dot { width: 100%; height: 100%; min-width: 6px; min-height: 6px; display: flex; align-items: center; justify-content: center; }
  .ravp-dot-inner { width: 6px; height: 6px; border-radius: 50%; border: 1.5px solid #1e293b; background: #00ff41; box-shadow: 0 0 6px rgba(0, 255, 65, 0.6); }
  .ravp-agents-layer { position: absolute; inset: 6%; z-index: 2; pointer-events: none; overflow: hidden; }
  .ravp-agent { position: absolute; width: 44px; height: 44px; opacity: 1; filter: drop-shadow(0 0 10px rgba(0, 255, 65, 0.4)); }
  .ravp-agent svg { width: 100%; height: 100%; }
  .ravp-agent-float1 { animation: ravp-float1 10s ease-in-out infinite; }
  .ravp-agent-float2 { animation: ravp-float2 11s ease-in-out infinite; }
  .ravp-agent-float3 { animation: ravp-float3 9s ease-in-out infinite; }
  .ravp-agent-float4 { animation: ravp-float4 12s ease-in-out infinite; }
  .ravp-agent-meet-left { animation: ravp-meet-left 7s ease-in-out infinite; }
  .ravp-agent-meet-right { animation: ravp-meet-right 7s ease-in-out infinite; }
  .ravp-agent-pair1 { animation: ravp-pair1 8s ease-in-out infinite; }
  .ravp-agent-pair2 { animation: ravp-pair2 8s ease-in-out infinite; }
  @keyframes ravp-float1 { 0%, 100% { transform: translate(0, 0) scale(1); } 25% { transform: translate(28px, -35px) scale(1.08); } 50% { transform: translate(-22px, 25px) scale(0.98); } 75% { transform: translate(35px, 28px) scale(1.05); } }
  @keyframes ravp-float2 { 0%, 100% { transform: translate(0, 0) scale(1); } 33% { transform: translate(-42px, 28px) scale(1.12); } 66% { transform: translate(32px, -32px) scale(0.95); } }
  @keyframes ravp-float3 { 0%, 100% { transform: translate(0, 0) rotate(0deg); } 50% { transform: translate(25px, 38px) rotate(8deg); } }
  @keyframes ravp-float4 { 0%, 100% { transform: translate(0, 0); } 25% { transform: translate(-32px, -22px); } 50% { transform: translate(-12px, 36px); } 75% { transform: translate(28px, -14px); } }
  @keyframes ravp-meet-left { 0%, 100% { transform: translate(0, 0) scale(1); } 45% { transform: translate(95px, 8px) scale(1.05); } 50% { transform: translate(100px, 10px) scale(1.25); } 55% { transform: translate(95px, 8px) scale(1.05); } }
  @keyframes ravp-meet-right { 0%, 100% { transform: translate(0, 0) scale(1); } 45% { transform: translate(-95px, -8px) scale(1.05); } 50% { transform: translate(-100px, -10px) scale(1.25); } 55% { transform: translate(-95px, -8px) scale(1.05); } }
  @keyframes ravp-pair1 { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(45px, -38px) scale(1.2); } }
  @keyframes ravp-pair2 { 0%, 100% { transform: translate(0, 0) scale(1); } 50% { transform: translate(-45px, 38px) scale(1.2); } }
  .ravp-welcome-box { position: relative; z-index: 2; padding: 1.5rem 2.5rem 1rem 2.5rem; display: flex; align-items: flex-start; justify-content: center; text-align: center; min-height: 380px; }
  .ravp-welcome-text { text-align: center; max-width: 960px; }
  .ravp-welcome-title { font-size: 11rem; font-weight: 700; color: #00ff41; letter-spacing: 0.02em; line-height: 1.12; margin: 0 0 0.75rem 0; text-shadow: 0 0 32px rgba(0, 255, 65, 0.55); }
  .ravp-login-hint { position: relative; z-index: 2; padding: 1.5rem 2.5rem 1.75rem 2.5rem; font-size: 1rem; color: #7fff9e; border-top: 1px solid rgba(0, 255, 65, 0.2); text-align: center; margin-top: auto; }
  @media (max-width: 900px) { .ravp-welcome-title { font-size: 5.5rem; } }
</style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "token" not in st.session_state:
    st.session_state.token = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "sidebar_selected_agent" not in st.session_state:
    st.session_state.sidebar_selected_agent = None
if "sidebar_selected_env" not in st.session_state:
    st.session_state.sidebar_selected_env = None

# Chat-only mode: opened in new window with ?agent_chat=agent_id&env=environment
_qp = st.query_params
_chat_agent_from_url = _qp.get("agent_chat")
if isinstance(_chat_agent_from_url, list):
    _chat_agent_from_url = _chat_agent_from_url[0] if _chat_agent_from_url else None
_chat_env_from_url = _qp.get("env")
if isinstance(_chat_env_from_url, list):
    _chat_env_from_url = _chat_env_from_url[0] if _chat_env_from_url else None
chat_only_mode = bool(_chat_agent_from_url)
chat_only_agent_id = _chat_agent_from_url if chat_only_mode else None
chat_only_env = _chat_env_from_url or "" if chat_only_mode else ""

def _render_chat(agent_id: str, key_prefix: str, environment: str | None = None):
    """Render chat input and send to deployed agent via control-plane proxy (sidebar or main)."""
    env = environment or st.session_state.get("sidebar_selected_env", "")
    qkey = f"{key_prefix}_query_{agent_id}_{env}"
    query = st.text_input("Ask the agent", key=qkey, placeholder="Type your question or request...", label_visibility="collapsed")
    if st.button("Send", key=f"{key_prefix}_send_{agent_id}_{env}"):
        st.session_state[f"{key_prefix}_last_query_{agent_id}_{env}"] = query
        st.rerun()
    last_q = st.session_state.get(f"{key_prefix}_last_query_{agent_id}_{env}")
    if last_q:
        # Call control-plane proxy to deployed agent (uses LLM in the agent pod)
        headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.get("token") else {}
        response_text = ""
        err = None
        if env:
            try:
                r = requests.post(
                    f"{API_BASE_URL}/api/v2/deployments/chat",
                    headers=headers,
                    json={"agent_id": agent_id, "environment": env, "message": last_q},
                    timeout=30,
                )
                if r.status_code == 200:
                    data = r.json()
                    response_text = data.get("response", "") or ""
                    if data.get("error"):
                        err = data.get("error")
                else:
                    err = r.text or f"Error {r.status_code}"
            except Exception as e:
                err = str(e)
        if err:
            st.caption("Error calling deployed agent")
            st.code(err, language="text")
        if response_text:
            st.caption("Agent response (LLM)")
            st.markdown(response_text)
        if not response_text and not err:
            st.caption("No response. Ensure the agent is deployed and running, and exposes /invoke.")

with st.sidebar:
    # Platform logo and branding
    if os.path.isfile(LOGO_PATH):
        st.image(LOGO_PATH, width=40)
    st.markdown("**Regulated Agent Vending Platform**")
    st.caption("RAVP v2")
    st.markdown("---")
    if chat_only_mode:
        st.caption(f"Chat with **{chat_only_agent_id}**")
        if st.button("← Back to main app", key="sidebar_chat_only_back"):
            st.query_params.clear()
            st.rerun()
        # Chat UI is in main area when in chat-only mode
    else:
        st.header("🔐 Login")
        if not st.session_state.logged_in:
            email = st.text_input("Email", value="admin@platform.com", help="Use admin@platform.com for Manage Tools / Policies")
            password = st.text_input("Password", type="password", value="demo")
            if st.button("Login", type="primary"):
                try:
                    r = requests.post(f"{API_BASE_URL}/api/v2/auth/login", json={"email": email, "password": password}, timeout=3)
                    if r.status_code == 200:
                        d = r.json()
                        st.session_state.logged_in = True
                        st.session_state.token = d.get("token")
                        u = d.get("user", {})
                        st.session_state.user_role = u.get("role", "agent_creator")
                        st.session_state.user_email = u.get("email", email)
                        st.rerun()
                    else:
                        st.error("Login failed")
                except Exception as e:
                    st.warning(f"API not reachable: {e}. Using demo login.")
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    admin_emails = {"admin@platform.com", "platform@admin.com"}
                    is_admin = email and email.strip().lower() in admin_emails
                    st.session_state.user_role = "platform_admin" if is_admin else "agent_creator"
                    st.session_state.token = "demo_platform_admin_offline" if is_admin else "demo_agent_creator"
                    st.rerun()
        else:
            role = st.session_state.user_role or "agent_creator"
            st.success(f"✅ {st.session_state.user_email or 'User'} ({role})")
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.token = None
                st.session_state.user_role = None
                st.session_state.user_email = None
                st.session_state.sidebar_selected_agent = None
                st.session_state.sidebar_selected_env = None
                st.rerun()

        # Deployed agents (sidebar): only when logged in – show running deployments for interactive chat
        if st.session_state.logged_in:
            st.markdown("---")
            st.subheader("🤖 Deployed Agents")
            _headers_sb = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.get("token") else {}
            try:
                _r_dep = requests.get(f"{API_BASE_URL}/api/v2/deployments", headers=_headers_sb, timeout=3)
                _sidebar_deployments = []
                if _r_dep.status_code == 200:
                    all_deps = _r_dep.json().get("deployments", [])
                    _sidebar_deployments = [
                        (d.get("agent_id"), d.get("environment", ""))
                        for d in all_deps
                        if d.get("status") == "running" and d.get("agent_id") and d.get("endpoint")
                    ]
            except Exception:
                _sidebar_deployments = []
            if _sidebar_deployments:
                if st.session_state.sidebar_selected_agent and st.session_state.sidebar_selected_env:
                    if st.button("← Back to platform", key="sidebar_back"):
                        st.session_state.sidebar_selected_agent = None
                        st.session_state.sidebar_selected_env = None
                        st.rerun()
                    _sel = st.session_state.sidebar_selected_agent
                    _env = st.session_state.sidebar_selected_env
                    st.caption(f"Chat with **{_sel}** ({_env})")
                    st.markdown(
                        f'<a href="?agent_chat={_sel}&env={_env}" target="_blank" rel="noopener noreferrer" style="font-size:0.85rem;">↗ Open in new window</a>',
                        unsafe_allow_html=True
                    )
                    st.markdown("---")
                    _render_chat(_sel, "sidebar", _env)
                else:
                    for _aid, _env in _sidebar_deployments:
                        _label = f"{_aid} ({_env})" if _env else _aid
                        _is_selected = (
                            st.session_state.sidebar_selected_agent == _aid
                            and st.session_state.sidebar_selected_env == _env
                        )
                        if st.button(
                            f"💬 {_label}" if not _is_selected else f"✓ {_label}",
                            key=f"sidebar_agent_{_aid}_{_env}",
                            type="primary" if _is_selected else "secondary",
                        ):
                            st.session_state.sidebar_selected_agent = _aid
                            st.session_state.sidebar_selected_env = _env
                            st.rerun()
            else:
                st.caption("No deployed agents (running) yet. Deploy from Deploy Agent or Browse Agents.")

# Main area: platform header (logo + title + tagline | cloud native)
header_col1, header_col2, header_col3 = st.columns([1, 10, 3])
with header_col1:
    if os.path.isfile(LOGO_PATH):
        st.image(LOGO_PATH, width=56)
with header_col2:
    st.markdown('<p class="ravp-main-title">Regulated Agent Vending Platform</p>', unsafe_allow_html=True)
    st.caption("RAVP v2")
    st.markdown('''
        <p class="ravp-platform-tagline">One platform for Agentic AI — <span class="ravp-tagline-actions"><strong>Build</strong><span class="ravp-tagline-sep">·</span><strong>Deploy</strong><span class="ravp-tagline-sep">·</span><strong>Govern</strong></span></p>
        ''', unsafe_allow_html=True)
with header_col3:
    # Cloud native platform: use icons from assets/cloud/ if present, else fallback
    _gcp_src = _load_cloud_icon_data_uri(["gcp", "gke"])   # GCP / Google Kubernetes Engine
    _aws_src = _load_cloud_icon_data_uri("aws")
    _azure_src = _load_cloud_icon_data_uri(["azure", "aks"])  # Azure / AKS
    _fallback_aws_svg = '''<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="28" height="28" title="AWS"><path fill="#FF9900" d="M6.763 10.036c0 .296.032.535.088.71.064.272.16.512.288.72.128.208.288.384.48.528.192.144.416.256.672.336.256.08.544.12.864.12.272 0 .52-.032.736-.096.224-.064.416-.16.576-.288.16-.128.288-.288.384-.48.096-.192.16-.416.192-.672l.832.192c-.064.352-.192.656-.384.912-.192.256-.432.472-.72.648-.288.176-.608.312-.96.408-.352.096-.72.144-1.104.144-.448 0-.848-.056-1.2-.168a2.587 2.587 0 0 1-.864-.48 2.378 2.378 0 0 1-.576-.768 2.304 2.304 0 0 1-.288-.984V9.988c0-.432.088-.8.264-1.104.176-.304.416-.544.72-.72.304-.176.648-.304 1.032-.384.384-.08.768-.12 1.152-.12.384 0 .736.04 1.056.12.32.08.608.2.864.36.256.16.472.352.648.576.176.224.304.48.384.768.08.288.12.592.12.912h-.032zm-.096-1.328c0-.272-.048-.512-.144-.72-.096-.208-.224-.384-.384-.528-.16-.144-.352-.256-.576-.336-.224-.08-.464-.12-.72-.12-.4 0-.752.088-1.056.264-.304.176-.544.416-.72.72-.176.304-.264.648-.264 1.032 0 .272.048.512.144.72.096.208.232.384.408.528.176.144.384.256.624.336.24.08.496.12.768.12.4 0 .752-.088 1.056-.264.304-.176.544-.416.72-.72.176-.304.264-.648.264-1.032z"/></svg>'''
    _fallback_azure_svg = '''<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" width="28" height="28" title="Azure"><path fill="#0078D4" d="M13.05 4.24L6.56 18.05l2.35-4.97 2.35-4.97 2.35 4.97 2.35 4.97-6.49-13.81zm.7 2.45l4.37 9.27 2.35-4.97 2.35-4.97h-6.54l-2.53 10.94zm-7.5 0l4.37 9.27 2.35-4.97 2.35-4.97H8.51L5.98 16.16z"/></svg>'''
    _logo_parts = []
    if _gcp_src:
        _logo_parts.append(f'<img src="{_gcp_src}" alt="" title="Google GKE" width="28" height="28" class="ravp-cloud-logo-img" />')
    else:
        _logo_parts.append('<img src="https://cdn.simpleicons.org/googlecloud/4285F4" alt="" title="Google GKE" width="28" height="28" class="ravp-cloud-logo-img" />')
    if _aws_src:
        _logo_parts.append(f'<img src="{_aws_src}" alt="" title="Amazon EKS" width="28" height="28" class="ravp-cloud-logo-img" />')
    else:
        _logo_parts.append('<span class="ravp-cloud-logo-inline" title="Amazon EKS">' + _fallback_aws_svg + '</span>')
    if _azure_src:
        _logo_parts.append(f'<img src="{_azure_src}" alt="" title="Azure AKS" width="28" height="28" class="ravp-cloud-logo-img" />')
    else:
        _logo_parts.append('<span class="ravp-cloud-logo-inline" title="Azure AKS">' + _fallback_azure_svg + '</span>')
    _cloud_logos_html = """
    <p class="ravp-cloud-native">Cloud native platform</p>
    <div class="ravp-cloud-logos">
      """ + "".join(_logo_parts) + """
    </div>
    """
    st.markdown(_cloud_logos_html, unsafe_allow_html=True)
st.markdown("---")

# Main area: when chat-only mode (opened in new window), show only the chat; otherwise show normal content
if chat_only_mode:
    # Chat-only view: main area is just the chat for this agent (env from URL for deployed agent)
    _chat_title = f"{chat_only_agent_id} ({chat_only_env})" if chat_only_env else chat_only_agent_id
    st.subheader(f"💬 Chat with **{_chat_title}**")
    _render_chat(chat_only_agent_id, "main_chat", chat_only_env)
    st.markdown("---")
    if st.button("← Back to main app", key="chat_only_back"):
        st.query_params.clear()
        st.rerun()
else:
    # Normal view: main area is the main page (tabs) or landing
    if not st.session_state.logged_in:
        # First page: full-width black box (welcome + dots + agents)
        _cols, _rows = 14, 9
        _dots_html = "".join(
            f'<div class="ravp-dot"><div class="ravp-dot-inner"></div></div>' for _ in range(_cols * _rows)
        )
        # Line-art robot SVGs (chatbot style: head, antennae, eyes, smile)
        _robot_svg_1 = '''<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="14" fill="none" stroke="#00ff41" stroke-width="1.8"/><line x1="18" y1="8" x2="18" y2="4" stroke="#00ff41" stroke-width="1.2"/><line x1="22" y1="8" x2="22" y2="4" stroke="#00ff41" stroke-width="1.2"/><circle cx="15" cy="18" r="2" fill="none" stroke="#00ff41" stroke-width="1.2"/><circle cx="25" cy="18" r="2" fill="none" stroke="#00ff41" stroke-width="1.2"/><path d="M 14 26 Q 20 31 26 26" fill="none" stroke="#00ff41" stroke-width="1.2"/></svg>'''
        _robot_svg_2 = '''<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><rect x="8" y="10" width="24" height="22" rx="4" fill="none" stroke="#b8ffc9" stroke-width="1.8"/><line x1="16" y1="6" x2="16" y2="2" stroke="#b8ffc9" stroke-width="1.2"/><line x1="24" y1="6" x2="24" y2="2" stroke="#b8ffc9" stroke-width="1.2"/><circle cx="16" cy="20" r="2.5" fill="none" stroke="#b8ffc9" stroke-width="1.2"/><circle cx="24" cy="20" r="2.5" fill="none" stroke="#b8ffc9" stroke-width="1.2"/><path d="M 15 28 Q 20 33 25 28" fill="none" stroke="#b8ffc9" stroke-width="1.2"/></svg>'''
        _robot_svg_3 = '''<svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="19" r="13" fill="none" stroke="#7fff9e" stroke-width="1.6"/><path d="M 18 5 L 18 2 M 22 5 L 22 2" stroke="#7fff9e" stroke-width="1.2" stroke-linecap="round"/><ellipse cx="15" cy="17" rx="2" ry="2.2" fill="none" stroke="#7fff9e" stroke-width="1.2"/><ellipse cx="25" cy="17" rx="2" ry="2.2" fill="none" stroke="#7fff9e" stroke-width="1.2"/><path d="M 13 26 Q 20 31 27 26" fill="none" stroke="#7fff9e" stroke-width="1.2"/></svg>'''
        _robot_svgs = [_robot_svg_1, _robot_svg_2, _robot_svg_3]
        _animations = ["ravp-agent-float1", "ravp-agent-float2", "ravp-agent-float3", "ravp-agent-float4", "ravp-agent-float1", "ravp-agent-float2", "ravp-agent-pair1", "ravp-agent-pair2", "ravp-agent-float3", "ravp-agent-float4", "ravp-agent-float1", "ravp-agent-float2"]
        _positions = [
            (14, 16), (28, 22), (70, 18), (82, 36), (18, 58), (78, 64), (38, 44), (58, 48),
            (46, 24), (54, 70), (30, 54), (66, 30)
        ]
        _agents_html = []
        for i, (left_pct, top_pct) in enumerate(_positions):
            _bot = _robot_svgs[i % len(_robot_svgs)]
            _anim = _animations[i % len(_animations)]
            _delay = random.uniform(0, 2.5)
            _agents_html.append(
                f'<span class="ravp-agent {_anim}" style="left: {left_pct}%; top: {top_pct}%; animation-delay: -{_delay:.1f}s;">{_bot}</span>'
            )
        _agents_html.append(f'<span class="ravp-agent ravp-agent-meet-left" style="left: 10%; top: 44%;">{_robot_svg_1}</span>')
        _agents_html.append(f'<span class="ravp-agent ravp-agent-meet-right" style="left: 80%; top: 46%;">{_robot_svg_2}</span>')
        _agents_layer_html = "".join(_agents_html)
        st.markdown(f"""
        <div class="ravp-landing-wrap">
          <div class="ravp-landing-bg"></div>
          <div class="ravp-welcome-box">
            <div class="ravp-welcome-text">
              <p class="ravp-welcome-title">Welcome to the world of agentic AI</p>
            </div>
          </div>
          <div class="ravp-dots-grid" aria-hidden="true">{_dots_html}</div>
          <div class="ravp-agents-layer" aria-hidden="true">{_agents_layer_html}</div>
          <div class="ravp-login-hint">Log in in the sidebar to get started.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Always show all tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "🏗️ Create Agent", "📋 My Agents", "🔍 Browse Agents", "🚀 Deploy Agent",
            "📦 Deployed Agents", "🛠️ Manage Tools", "📜 Manage Policies", "📊 Version History", "📺 How it works"
        ])
        is_admin = st.session_state.user_role == "platform_admin"
        headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    
        with tab1:
            st.header("Create New Agent")
            if not st.session_state.logged_in:
                st.warning("Please log in to create agents.")
            else:
                try:
                    r = requests.get(f"{API_BASE_URL}/tools", timeout=2)
                    tool_list = [t.get("name") for t in r.json().get("tools", []) if t.get("name")] if r.status_code == 200 else []
                except Exception:
                    tool_list = ["get_payment_exception", "get_customer_profile", "get_service_metrics", "check_slo_status"]
                if not tool_list:
                    tool_list = ["get_payment_exception", "get_customer_profile"]
                
                # Fetch available policies
                policy_list = []
                try:
                    r_policies = requests.get(f"{API_BASE_URL}/policies", timeout=2)
                    if r_policies.status_code == 200:
                        policy_list = [p.get("id") for p in r_policies.json().get("policies", []) if p.get("id")]
                    # Fallback: try admin endpoint if user is admin
                    elif is_admin:
                        try:
                            r_admin_policies = requests.get(f"{API_BASE_URL}/api/v2/admin/policies", headers=headers, timeout=2)
                            if r_admin_policies.status_code == 200:
                                policy_list = [p.get("policy_id") for p in r_admin_policies.json().get("policies", []) if p.get("policy_id")]
                        except Exception:
                            pass
                except Exception:
                    # Fallback examples if API unavailable
                    policy_list = ["payments/retry", "payments/approval", "fraud/block"]
                
                # Fetch available Gemini models (from Google AI Studio when API key set)
                model_list = []
                try:
                    r_models = requests.get(f"{API_BASE_URL}/api/v2/models", timeout=2)
                    if r_models.status_code == 200:
                        model_list = r_models.json().get("models", [])
                except Exception:
                    pass
                if not model_list:
                    model_list = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
                
                col1, col2 = st.columns(2)
                with col1:
                    agent_id = st.text_input("Agent ID", value="my_agent", help="Unique identifier (e.g., payment_failed)")
                    domain_options = ["payments", "fraud", "customer_service", "cloud_platform", "infrastructure", "general"]
                    domain_choice = st.selectbox(
                        "Domain",
                        options=domain_options + ["Other"],
                        index=domain_options.index("general"),
                        help="Determines which section the agent appears under in Browse Agents (e.g. Payments, Cloud Platform)."
                    )
                    if domain_choice == "Other":
                        domain = st.text_input("Custom domain", value="general", key="domain_custom", help="e.g. analytics, compliance")
                    else:
                        domain = domain_choice
                    risk_tier = st.selectbox("Risk Tier", ["low", "medium", "high"], index=0)
                    version = st.text_input("Version", value="1.0.0")
                
                with col2:
                    goal = st.text_area("Purpose / Goal", value="What this agent does", height=100,
                        help="Why this agent exists - the business mission or objective")
                    model_options = ["Auto (recommended)"] + model_list
                    model_display = st.selectbox(
                        "Model",
                        options=model_options,
                        index=0,
                        help="Auto lets the agent use a balanced default (e.g. gemini-2.5-flash). Or pick a specific Gemini model from Google AI Studio."
                    )
                    model = "auto" if model_display == "Auto (recommended)" else model_display
                    confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.7, 0.1)
                    human_in_the_loop = st.checkbox("Human in the Loop", value=True)
                
                # Skills - high-level capabilities
                st.markdown("### 🎯 Skills (Capabilities)")
                st.caption("What can this agent do? Skills are used for discovery, routing, and LLM context.")
                
                skills_input = st.text_input(
                    "Enter skills (comma-separated)",
                    placeholder="e.g., incident_investigation, log_analysis, metric_analysis",
                    help="Examples: incident_investigation, payment_processing, fraud_detection, customer_communication"
                )
                skills = [s.strip() for s in skills_input.split(",") if s.strip()] if skills_input else []
                if skills:
                    st.caption(f"Skills: {', '.join(skills)}")
                
                st.markdown("### 🛠️ Tools & Policies")
                selected_tools = st.multiselect("Allowed Tools", tool_list, default=tool_list[:2] if len(tool_list) >= 2 else tool_list,
                    help="Technical tools this agent can execute")
                
                if policy_list:
                    selected_policies = st.multiselect("Policies", policy_list, help="Select policies from registry (e.g., payments/retry)")
                else:
                    st.info("No policies available. Create policies in the 'Manage Policies' tab (admin only).")
                    selected_policies = []
                
                st.caption(f"Tools from registry ({len(tool_list)} available). Policies from registry ({len(policy_list)} available).")
                
                if st.button("Create Agent", type="primary"):
                    if not agent_id or not goal:
                        st.error("Agent ID and Purpose/Goal are required.")
                    else:
                        try:
                            # Build agent definition
                            agent_def = {
                                "agent_id": agent_id,
                                "version": version,
                                "domain": domain,
                                "risk_tier": risk_tier,
                                "purpose": {
                                    "goal": goal
                                },
                                "skills": skills,
                                "allowed_tools": selected_tools,
                                "policies": selected_policies,
                                "model": model if model else None,
                                "confidence_threshold": confidence_threshold,
                                "human_in_the_loop": human_in_the_loop
                            }
                            
                            # Make API call
                            r = requests.post(
                                f"{API_BASE_URL}/api/v2/agent-definitions",
                                json=agent_def,
                                headers=headers,
                                timeout=5
                            )
                            
                            if r.status_code == 200:
                                response = r.json()
                                st.success(f"✅ Agent '{agent_id}' created successfully!")
                                
                                # Show code generation status prominently
                                if "code_generation" in response:
                                    code_gen = response["code_generation"]
                                    if code_gen.get("success"):
                                        st.success(f"🔧 Agent code generated at: `{code_gen.get('path', 'N/A')}`")
                                        st.info("💡 Your agent is ready to build and deploy!")
                                    else:
                                        st.warning(f"⚠️ Code generation issue: {code_gen.get('message', 'Unknown error')}")
                                        st.info("You can manually generate code later from the Deploy tab.")
                                else:
                                    st.info("ℹ️ Agent definition created. Code may need to be generated manually.")
                                
                                # Show full response in expandable section
                                with st.expander("📋 View Full Response"):
                                    st.json(response)
                                
                                st.rerun()
                            elif r.status_code == 400:
                                st.error(f"Validation error: {r.json().get('detail', r.text)}")
                            elif r.status_code == 401:
                                st.error("Not authenticated. Please log in.")
                            else:
                                st.error(f"Error {r.status_code}: {r.text}")
                        except Exception as e:
                            st.error(f"Failed to create agent: {e}")
    
        with tab2:
            st.header("My Agents")
            st.caption("Agents you created (filtered by creator)")
            try:
                # Get all agents and filter by creator
                headers_with_email = headers.copy()
                if st.session_state.get("user_email"):
                    headers_with_email["X-User-Email"] = st.session_state.user_email
                r = requests.get(f"{API_BASE_URL}/agents", headers=headers_with_email, timeout=3)
                if r.status_code == 200:
                    all_agents = r.json().get("agents", [])
                    # Filter to only show agents created by current user
                    user_email = st.session_state.get("user_email", "").lower()
                    my_agents = []
                    for agent_info in all_agents:
                        agent_id = agent_info.get("agent_id", "")
                        # Load full definition to check creator
                        try:
                            r2 = requests.get(f"{API_BASE_URL}/api/v2/agent-definitions/{agent_id}", headers=headers, timeout=2)
                            if r2.status_code == 200:
                                agent_def = r2.json()
                                rbac = agent_def.get("rbac", {})
                                creator = rbac.get("creator", "").lower()
                                # Show if user is creator or platform admin
                                if user_email == creator or st.session_state.user_role == "platform_admin":
                                    my_agents.append(agent_info)
                        except Exception:
                            pass
                    
                    if my_agents:
                        for agent_info in my_agents:
                            agent_id = agent_info.get("agent_id", "")
                            version = agent_info.get("version", "1.0.0")
                            with st.expander(f"🤖 {agent_id} (v{version})"):
                                try:
                                    r2 = requests.get(f"{API_BASE_URL}/api/v2/agent-definitions/{agent_id}", headers=headers, timeout=2)
                                    if r2.status_code == 200:
                                        agent_def = r2.json()
                                        
                                        # Display agent details
                                        col1, col2 = st.columns([2, 1])
                                        with col1:
                                            # Show tools and policies for current version
                                            allowed_tools = agent_def.get("allowed_tools", [])
                                            policies = agent_def.get("policies", [])
                                            
                                            if allowed_tools or policies:
                                                st.markdown("### 🔧 Tools & Policies")
                                                
                                                # Display Tools with versions
                                                if allowed_tools:
                                                    st.markdown("**Tools:**")
                                                    # Build tool domain map
                                                    tool_domains_map = {}
                                                    try:
                                                        r_domains = requests.get(f"{API_BASE_URL}/api/v2/admin/tools/domains", headers=headers, timeout=2)
                                                        if r_domains.status_code == 200:
                                                            domains_data = r_domains.json().get("domains", [])
                                                            for dom in domains_data:
                                                                domain_name = dom.get("domain", "")
                                                                tools_list = dom.get("tools", [])
                                                                for t in tools_list:
                                                                    tool_id = t.get("tool_id") or t.get("name", "")
                                                                    if tool_id:
                                                                        tool_domains_map[tool_id] = domain_name
                                                    except Exception:
                                                        pass
                                                    
                                                    for tool_id in allowed_tools:
                                                        tool_version = "N/A"
                                                        tool_domain = tool_domains_map.get(tool_id, "general")
                                                        try:
                                                            r_tool = requests.get(
                                                                f"{API_BASE_URL}/api/v2/admin/tools/by-domain/{tool_domain}/{tool_id}",
                                                                headers=headers,
                                                                timeout=2
                                                            )
                                                            if r_tool.status_code == 200:
                                                                tool_data = r_tool.json()
                                                                tool_version = tool_data.get("version", "1.0.0")
                                                        except Exception:
                                                            try:
                                                                r_tool_flat = requests.get(f"{API_BASE_URL}/tools", timeout=2)
                                                                if r_tool_flat.status_code == 200:
                                                                    tools_dict = r_tool_flat.json().get("tools", {})
                                                                    if isinstance(tools_dict, dict) and tool_id in tools_dict:
                                                                        tool_version = tools_dict[tool_id].get("version", "1.0.0")
                                                            except Exception:
                                                                pass
                                                        st.write(f"- **{tool_id}** (v{tool_version})")
                                                
                                                # Display Policies
                                                if policies:
                                                    st.markdown("**Policies:**")
                                                    for policy_id in policies:
                                                        st.write(f"- **{policy_id}**")
                                                
                                                st.divider()
                                            
                                            st.json(agent_def)
                                        with col2:
                                            st.subheader("Actions")
                                            
                                            # Update button
                                            if st.button(f"✏️ Update {agent_id}", key=f"update_{agent_id}", type="primary"):
                                                st.session_state[f"editing_{agent_id}"] = True
                                                st.session_state[f"edit_agent_def_{agent_id}"] = agent_def
                                                st.rerun()
                                            
                                            # Delete button
                                            if st.button(f"🗑️ Delete {agent_id}", key=f"del_{agent_id}", type="secondary"):
                                                r3 = requests.delete(f"{API_BASE_URL}/api/v2/agent-definitions/{agent_id}", headers=headers, timeout=3)
                                                if r3.status_code == 200:
                                                    st.success(f"Deleted {agent_id}")
                                                    st.rerun()
                                                else:
                                                    st.error(f"Error: {r3.text}")
                                            
                                            # View history button
                                            if st.button(f"📊 History", key=f"history_{agent_id}"):
                                                st.session_state[f"view_history_{agent_id}"] = True
                                                st.rerun()
                                        
                                        # Update form (if editing)
                                        if st.session_state.get(f"editing_{agent_id}", False):
                                            st.divider()
                                            st.subheader(f"Update Agent: {agent_id}")
                                            edit_def = st.session_state.get(f"edit_agent_def_{agent_id}", agent_def)
                                            
                                            # Fetch tools and policies for update form
                                            try:
                                                r_tools = requests.get(f"{API_BASE_URL}/tools", timeout=2)
                                                tool_list = [t.get("name") for t in r_tools.json().get("tools", []) if t.get("name")] if r_tools.status_code == 200 else []
                                            except Exception:
                                                tool_list = []
                                            
                                            try:
                                                r_policies = requests.get(f"{API_BASE_URL}/policies", timeout=2)
                                                policy_list = [p.get("id") for p in r_policies.json().get("policies", []) if p.get("id")] if r_policies.status_code == 200 else []
                                            except Exception:
                                                policy_list = []
                                            
                                            try:
                                                r_models = requests.get(f"{API_BASE_URL}/api/v2/models", timeout=2)
                                                upd_model_list = r_models.json().get("models", []) if r_models.status_code == 200 else []
                                            except Exception:
                                                upd_model_list = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
                                            if not upd_model_list:
                                                upd_model_list = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
                                            upd_model_options = ["Auto (recommended)"] + upd_model_list
                                            current_model = edit_def.get("model") or ""
                                            if not current_model or current_model.strip().lower() == "auto":
                                                upd_model_index = 0
                                            elif current_model in upd_model_list:
                                                upd_model_index = upd_model_list.index(current_model) + 1
                                            else:
                                                upd_model_options = [current_model] + upd_model_options
                                                upd_model_index = 0
                                            
                                            # Update form fields
                                            upd_col1, upd_col2 = st.columns(2)
                                            with upd_col1:
                                                upd_domain = st.text_input("Domain", value=edit_def.get("domain", "general"), key=f"upd_domain_{agent_id}")
                                                upd_risk_tier = st.selectbox("Risk Tier", ["low", "medium", "high"], 
                                                    index=["low", "medium", "high"].index(edit_def.get("risk_tier", "low")), 
                                                    key=f"upd_risk_{agent_id}")
                                                upd_version = st.text_input("Version", value=edit_def.get("version", "1.0.0"), key=f"upd_version_{agent_id}")
                                            
                                            with upd_col2:
                                                upd_goal = st.text_area("Purpose / Goal", 
                                                    value=edit_def.get("purpose", {}).get("goal", ""), 
                                                    height=100, key=f"upd_goal_{agent_id}",
                                                    help="Why this agent exists - the business mission")
                                                upd_model_display = st.selectbox("Model", options=upd_model_options, index=upd_model_index, key=f"upd_model_{agent_id}")
                                                upd_model = "auto" if upd_model_display == "Auto (recommended)" else upd_model_display
                                                upd_confidence = st.slider("Confidence Threshold", 0.0, 1.0, 
                                                    float(edit_def.get("confidence_threshold", 0.7)), 0.1, key=f"upd_conf_{agent_id}")
                                                upd_hitl = st.checkbox("Human in the Loop", 
                                                    value=edit_def.get("human_in_the_loop", True), key=f"upd_hitl_{agent_id}")
                                            
                                            # Skills
                                            st.markdown("### 🎯 Skills")
                                            existing_skills = edit_def.get("skills", [])
                                            upd_skills_input = st.text_input(
                                                "Skills (comma-separated)",
                                                value=", ".join(existing_skills) if existing_skills else "",
                                                key=f"upd_skills_{agent_id}",
                                                help="High-level capabilities: incident_investigation, payment_processing, etc."
                                            )
                                            upd_skills = [s.strip() for s in upd_skills_input.split(",") if s.strip()] if upd_skills_input else []
                                            
                                            st.markdown("### 🛠️ Tools & Policies")
                                            upd_tools = st.multiselect("Allowed Tools", tool_list, 
                                                default=edit_def.get("allowed_tools", []), key=f"upd_tools_{agent_id}")
                                            upd_policies = st.multiselect("Policies", policy_list, 
                                                default=edit_def.get("policies", []), key=f"upd_policies_{agent_id}")
                                            
                                            upd_col_btn1, upd_col_btn2 = st.columns(2)
                                            with upd_col_btn1:
                                                if st.button("💾 Save Changes", key=f"save_{agent_id}", type="primary"):
                                                    try:
                                                        update_def = {
                                                            "domain": upd_domain,
                                                            "risk_tier": upd_risk_tier,
                                                            "version": upd_version,
                                                            "purpose": {"goal": upd_goal},
                                                            "skills": upd_skills,
                                                            "allowed_tools": upd_tools,
                                                            "policies": upd_policies,
                                                            "model": upd_model if upd_model else None,
                                                            "confidence_threshold": upd_confidence,
                                                            "human_in_the_loop": upd_hitl
                                                        }
                                                        
                                                        r_upd = requests.put(
                                                            f"{API_BASE_URL}/api/v2/agent-definitions/{agent_id}",
                                                            json=update_def,
                                                            headers=headers,
                                                            timeout=5
                                                        )
                                                        
                                                        if r_upd.status_code == 200:
                                                            st.success(f"✅ Agent '{agent_id}' updated!")
                                                            result = r_upd.json()
                                                            if "version" in result:
                                                                st.info(f"Version: {result['version']['old']} → {result['version']['new']}")
                                                            st.session_state[f"editing_{agent_id}"] = False
                                                            st.rerun()
                                                        else:
                                                            st.error(f"Error {r_upd.status_code}: {r_upd.text}")
                                                    except Exception as e:
                                                        st.error(f"Failed to update agent: {e}")
                                            
                                            with upd_col_btn2:
                                                if st.button("❌ Cancel", key=f"cancel_{agent_id}"):
                                                    st.session_state[f"editing_{agent_id}"] = False
                                                    st.rerun()
                                        
                                        # Version history view
                                        if st.session_state.get(f"view_history_{agent_id}", False):
                                            st.divider()
                                            st.subheader(f"Version History: {agent_id}")
                                            try:
                                                r_history = requests.get(f"{API_BASE_URL}/api/v2/agent-definitions/{agent_id}/history", headers=headers, timeout=2)
                                                if r_history.status_code == 200:
                                                    history_data = r_history.json()
                                                    st.write(f"**Current Version:** {history_data.get('current_version', 'N/A')}")
                                                    st.write(f"**Total Versions:** {history_data.get('total_versions', 0)}")
                                                    
                                                    history = history_data.get("history", [])
                                                    if history:
                                                        for entry in history:
                                                            version = entry.get('version', 'N/A')
                                                            with st.expander(f"Version {version} (from {entry.get('previous_version')})"):
                                                                st.write(f"**Timestamp:** {entry.get('timestamp', 'N/A')}")
                                                                changes = entry.get("changes", {})
                                                                if changes:
                                                                    st.write("**Changes:**")
                                                                    if changes.get("major"):
                                                                        st.write("- **MAJOR:**", ", ".join(changes["major"]))
                                                                    if changes.get("minor"):
                                                                        st.write("- **MINOR:**", ", ".join(changes["minor"]))
                                                                    if changes.get("patch"):
                                                                        st.write("- **PATCH:**", ", ".join(changes["patch"]))
                                                                
                                                                # Fetch agent definition for this specific version to get tools and policies
                                                                try:
                                                                    r_agent_version = requests.get(
                                                                        f"{API_BASE_URL}/agents/{agent_id}?version={version}",
                                                                        headers=headers,
                                                                        timeout=2
                                                                    )
                                                                    if r_agent_version.status_code == 200:
                                                                        agent_def_version = r_agent_version.json()
                                                                        allowed_tools_v = agent_def_version.get("allowed_tools", [])
                                                                        policies_v = agent_def_version.get("policies", [])
                                                                        
                                                                        # Display Tools with versions
                                                                        if allowed_tools_v:
                                                                            st.divider()
                                                                            st.write("**🔧 Tools:**")
                                                                            # Build tool domain map
                                                                            tool_domains_map_v = {}
                                                                            try:
                                                                                r_domains_v = requests.get(f"{API_BASE_URL}/api/v2/admin/tools/domains", headers=headers, timeout=2)
                                                                                if r_domains_v.status_code == 200:
                                                                                    domains_data_v = r_domains_v.json().get("domains", [])
                                                                                    for dom in domains_data_v:
                                                                                        domain_name = dom.get("domain", "")
                                                                                        tools_list = dom.get("tools", [])
                                                                                        for t in tools_list:
                                                                                            tool_id = t.get("tool_id") or t.get("name", "")
                                                                                            if tool_id:
                                                                                                tool_domains_map_v[tool_id] = domain_name
                                                                            except Exception:
                                                                                pass
                                                                            
                                                                            for tool_id in allowed_tools_v:
                                                                                tool_version_v = "N/A"
                                                                                tool_domain_v = tool_domains_map_v.get(tool_id, "general")
                                                                                try:
                                                                                    r_tool_v = requests.get(
                                                                                        f"{API_BASE_URL}/api/v2/admin/tools/by-domain/{tool_domain_v}/{tool_id}",
                                                                                        headers=headers,
                                                                                        timeout=2
                                                                                    )
                                                                                    if r_tool_v.status_code == 200:
                                                                                        tool_data_v = r_tool_v.json()
                                                                                        tool_version_v = tool_data_v.get("version", "1.0.0")
                                                                                except Exception:
                                                                                    try:
                                                                                        r_tool_flat_v = requests.get(f"{API_BASE_URL}/tools", timeout=2)
                                                                                        if r_tool_flat_v.status_code == 200:
                                                                                            tools_dict_v = r_tool_flat_v.json().get("tools", {})
                                                                                            if isinstance(tools_dict_v, dict) and tool_id in tools_dict_v:
                                                                                                tool_version_v = tools_dict_v[tool_id].get("version", "1.0.0")
                                                                                    except Exception:
                                                                                        pass
                                                                                st.write(f"- **{tool_id}** (v{tool_version_v})")
                                                                        
                                                                        # Display Policies
                                                                        if policies_v:
                                                                            st.divider()
                                                                            st.write("**📜 Policies:**")
                                                                            for policy_id in policies_v:
                                                                                st.write(f"- **{policy_id}**")
                                                                except Exception:
                                                                    pass
                                                    else:
                                                        st.info("No version history available.")
                                                    
                                                    if st.button("Close History", key=f"close_history_{agent_id}"):
                                                        st.session_state[f"view_history_{agent_id}"] = False
                                                        st.rerun()
                                                else:
                                                    st.warning("Could not load version history.")
                                            except Exception as e:
                                                st.warning(f"Error loading history: {e}")
                                except Exception as e:
                                    st.warning(f"Could not load details: {e}")
                    else:
                        st.info("No agents found. Create one in the 'Create Agent' tab.")
                elif r.status_code == 401:
                    st.warning("Please log in to view your agents.")
                else:
                    st.error(f"Error {r.status_code}: {r.text}")
            except Exception as e:
                st.warning(f"API not reachable: {e}. Agents may be available via config/agents/.")
    
        with tab3:
            st.header("Browse Agents")
            st.caption("All agents you can view (filtered by RBAC permissions). Grouped by Business, Cloud, Platform.")
            try:
                headers_with_email = headers.copy()
                if st.session_state.get("user_email"):
                    headers_with_email["X-User-Email"] = st.session_state.user_email
                r = requests.get(f"{API_BASE_URL}/agents", headers=headers_with_email, timeout=3)
                if r.status_code == 200:
                    agents = r.json().get("agents", [])
                    if agents:
                        # Group agents by domain (payments, fraud, cloud_platform, etc.)
                        domain_order = ["payments", "fraud", "customer_service", "cloud_platform", "infrastructure", "general"]
                        domain_labels = {
                            "payments": "Payments", "fraud": "Fraud", "customer_service": "Customer Service",
                            "cloud_platform": "Cloud Platform", "infrastructure": "Infrastructure", "general": "General"
                        }
                        by_domain = {}
                        for agent_info in agents:
                            d = agent_info.get("domain") or "Other"
                            by_domain.setdefault(d, []).append(agent_info)
                        # Render sections: known domains in order, then any other domains, then "Other"
                        ordered_domains = [x for x in domain_order if x in by_domain]
                        ordered_domains += sorted(k for k in by_domain if k not in domain_order and k != "Other")
                        if "Other" in by_domain:
                            ordered_domains.append("Other")
                        for d in ordered_domains:
                            label = domain_labels.get(d, d.replace("_", " ").title() if d != "Other" else "Other")
                            st.subheader(f"📁 {label}")
                            for agent_info in by_domain[d]:
                                agent_id = agent_info.get("agent_id", "")
                                version = agent_info.get("version", "1.0.0")
                                permissions = agent_info.get("permissions", {})
                                can_view = permissions.get("can_view", False)
                                can_use = permissions.get("can_use", False)
                                can_edit = permissions.get("can_edit", False)
                                
                                # Build permission badges
                                badges = []
                                if can_view:
                                    badges.append("👁️ View")
                                if can_use:
                                    badges.append("✅ Use")
                                if can_edit:
                                    badges.append("✏️ Edit")
                                
                                badge_text = " | ".join(badges) if badges else "❌ No Access"
                                
                                # Simple card view with action icons
                                col_info, col_actions = st.columns([4, 1])
                                
                                with col_info:
                                    st.markdown(f"**🤖 {agent_id}** `v{version}`")
                                    
                                    # Show purpose if available
                                    try:
                                        r2 = requests.get(f"{API_BASE_URL}/agents/{agent_id}", headers=headers, timeout=2)
                                        if r2.status_code == 200:
                                            agent_def = r2.json()
                                            purpose = agent_def.get("purpose", {}).get("goal", "")
                                            if purpose:
                                                st.caption(f"{purpose[:100]}..." if len(purpose) > 100 else purpose)
                                    except Exception:
                                        pass
                                
                                with col_actions:
                                    st.markdown("**Actions**")
                                    action_cols = st.columns(3)
                                    
                                    # View icon
                                    with action_cols[0]:
                                        if can_view:
                                            if st.button("👁️", key=f"view_{agent_id}", help="View Details"):
                                                st.session_state[f"viewing_{agent_id}"] = True
                                                st.rerun()
                                    
                                    # Edit icon
                                    with action_cols[1]:
                                        if can_edit:
                                            if st.button("✏️", key=f"edit_{agent_id}", help="Edit Agent"):
                                                st.session_state[f"editing_{agent_id}"] = True
                                                st.rerun()
                                    
                                    # Deploy icon
                                    with action_cols[2]:
                                        if can_use:
                                            if st.button("🚀", key=f"deploy_{agent_id}", help="Deploy"):
                                                st.session_state[f"deploying_{agent_id}"] = True
                                                st.rerun()
                                
                                # Show deployment count if deployed
                                try:
                                    r_deployments = requests.get(
                                        f"{API_BASE_URL}/api/v2/deployments/{agent_id}",
                                        headers=headers,
                                        timeout=2
                                    )
                                    if r_deployments.status_code == 200:
                                        deployments = r_deployments.json().get("deployments", [])
                                        if deployments:
                                            with col_info:
                                                st.caption(f"📦 Deployed in {len(deployments)} environment(s)")
                                except Exception:
                                    pass
                                
                                st.divider()
                                
                                # Show detailed view if requested
                                if st.session_state.get(f"viewing_{agent_id}"):
                                    with st.expander(f"📋 Details for {agent_id}", expanded=True):
                                        try:
                                            r2 = requests.get(f"{API_BASE_URL}/agents/{agent_id}", headers=headers, timeout=2)
                                            if r2.status_code == 200:
                                                agent_def = r2.json()
                                                st.json(agent_def)
                                            if st.button("Close Details", key=f"close_view_{agent_id}"):
                                                st.session_state[f"viewing_{agent_id}"] = False
                                                st.rerun()
                                        except Exception as e:
                                            st.error(f"Could not load details: {e}")
                                
                                # Show edit form if requested
                                if st.session_state.get(f"editing_{agent_id}"):
                                    with st.expander(f"✏️ Edit {agent_id}", expanded=True):
                                        st.info("Navigate to 'My Agents' tab to edit agent details")
                                        if st.button("Close", key=f"close_edit_{agent_id}"):
                                            st.session_state[f"editing_{agent_id}"] = False
                                            st.rerun()
                                
                                # Deploy workflow if requested
                                if can_use and st.session_state.get(f"deploying_{agent_id}"):
                                    with st.expander(f"🚀 Deploy {agent_id}", expanded=True):
                                        st.info("Navigate to 'Deploy Agent' tab and select this agent for full deployment options")
                                        if st.button("Close", key=f"close_deploy_{agent_id}"):
                                            st.session_state[f"deploying_{agent_id}"] = False
                                            st.rerun()
                    else:
                        st.info("No agents available that you have permission to view.")
                elif r.status_code == 401:
                    st.warning("Please log in to browse agents.")
                else:
                    st.error(f"Error {r.status_code}: {r.text}")
            except Exception as e:
                st.warning(f"API not reachable: {e}")
    
        with tab4:
            st.header("🚀 Deploy Agent")
            if not st.session_state.logged_in:
                st.warning("Please log in to deploy agents.")
            else:
                # Docker status hint when Build & Push is used
                try:
                    r_docker = requests.get(f"{API_BASE_URL}/api/v2/docker/status", headers=headers, timeout=2)
                    if r_docker.status_code == 200 and not r_docker.json().get("available"):
                        st.info(
                            "💡 **Build & Push** requires Docker on the machine running the control plane. "
                            "Start Docker Desktop there, or build images in CI/CD and only record deployments here. "
                            "See [Where to Run the Platform](docs/WHERE-TO-RUN-PLATFORM.md)."
                        )
                except Exception:
                    pass
                # Get list of agents
                try:
                    r_agents = requests.get(f"{API_BASE_URL}/api/v2/agent-definitions", headers=headers, timeout=3)
                    agents_list = []
                    if r_agents.status_code == 200:
                        agents_list = [a.get("agent_id") for a in r_agents.json().get("agents", [])]
                except Exception:
                    agents_list = []
                
                if not agents_list:
                    st.info("No agents available. Create an agent first.")
                else:
                    selected_agent = st.selectbox("Select Agent to Deploy", agents_list)
                    
                    # Check if agent code exists
                    code_exists = False
                    code_status_message = ""
                    try:
                        r_code = requests.get(f"{API_BASE_URL}/api/v2/code-gen/validate/{selected_agent}", headers=headers, timeout=2)
                        if r_code.status_code == 200:
                            code_data = r_code.json()
                            code_exists = code_data.get("code_exists", False)
                            if code_exists:
                                st.success(f"✅ Agent code is ready")
                            else:
                                st.warning(f"⚠️ Agent code not found. Generate it first!")
                                if st.button("🔧 Generate Agent Code", key="gen_code_deploy"):
                                    try:
                                        r_gen = requests.post(
                                            f"{API_BASE_URL}/api/v2/code-gen/generate",
                                            json={"agent_id": selected_agent, "overwrite": False},
                                            headers=headers,
                                            timeout=10
                                        )
                                        if r_gen.status_code == 200:
                                            st.success("✅ Agent code generated successfully!")
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to generate code: {r_gen.text}")
                                    except Exception as e:
                                        st.error(f"Error generating code: {e}")
                    except Exception:
                        st.info("💡 Unable to verify if agent code exists. Proceed with caution.")
                    
                    deployment_target = st.radio(
                        "Deployment Target",
                        ["Local (Docker)", "GKE (Google)", "AKS (Azure)", "EKS (AWS)", "Cloud Run"],
                        horizontal=True
                    )
                    
                    if selected_agent and code_exists:
                        # Get agent details
                        try:
                            r_agent = requests.get(f"{API_BASE_URL}/api/v2/agent-definitions/{selected_agent}", headers=headers, timeout=2)
                            if r_agent.status_code == 200:
                                agent_details = r_agent.json()
                                
                                st.divider()
                                
                                if deployment_target == "Local (Docker)":
                                    st.subheader("🐳 Local Docker Deployment")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        docker_image_name = st.text_input("Docker Image Name", 
                                            value=f"agent-{selected_agent.lower()}", 
                                            help="Name for the Docker image")
                                        docker_tag = st.text_input("Tag", value="latest", help="Image tag")
                                        port = st.number_input("Port", value=8080, min_value=1000, max_value=65535)
                                    
                                    with col2:
                                        control_plane_url = st.text_input("Control Plane URL", 
                                            value="http://localhost:8010",
                                            help="URL of the control-plane API")
                                        env_vars = st.text_area("Additional Environment Variables (one per line, KEY=VALUE)",
                                            height=100,
                                            help="Optional: Additional environment variables")
                                    
                                    # LLM Configuration Section
                                    st.divider()
                                    st.subheader("🤖 LLM Configuration (Runtime)")
                                    st.caption("Configure which LLM service this deployment should use")
                                    
                                    llm_col1, llm_col2 = st.columns(2)
                                    with llm_col1:
                                        google_api_key = st.text_input("API Key", type="password",
                                            help="API key for LLM access (Google AI Studio, Vertex AI, etc.)")
                                        llm_provider = st.selectbox("Provider (optional)", 
                                            ["auto", "google", "vertex_ai", "openai", "anthropic"],
                                            help="Leave as 'auto' to detect from model name")
                                    with llm_col2:
                                        llm_endpoint = st.text_input("Custom Endpoint (optional)",
                                            placeholder="https://your-vertex-endpoint.com",
                                            help="Custom endpoint for Vertex AI, corporate proxy, etc.")
                                        llm_project = st.text_input("GCP Project (for Vertex AI, optional)",
                                            placeholder="your-gcp-project",
                                            help="Required for Vertex AI provider")
                                    
                                    st.markdown("### Deployment Commands")
                                    
                                    # Generate Dockerfile
                                    dockerfile_content = f"""FROM python:3.11-slim
    
    WORKDIR /app
    
    # Install dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    # Copy agent code
    COPY agents/{selected_agent}/ ./agents/{selected_agent}/
    COPY agent-sdk/ ./agent-sdk/
    COPY config/ ./config/
    
    # Set environment variables
    ENV CONTROL_PLANE_URL={control_plane_url}
    ENV GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
    ENV PYTHONPATH=/app
    
    # Expose port
    EXPOSE {port}
    
    # Run agent
    CMD ["python", "-m", "agents.{selected_agent}.agent"]
    """
                                    
                                    with st.expander("📄 Dockerfile"):
                                        st.code(dockerfile_content, language="dockerfile")
                                    
                                    # Generate docker commands with LLM config
                                    docker_commands = f"""# Build Docker image
    docker build -t {docker_image_name}:{docker_tag} -f Dockerfile.agent .
    
    # Run container locally with LLM configuration
    docker run -d \\
      --name {selected_agent} \\
      -p {port}:{port} \\
      -e CONTROL_PLANE_URL="{control_plane_url}" \\
      -e GOOGLE_API_KEY="{google_api_key if google_api_key else '$GOOGLE_API_KEY'}" \\"""
                                    
                                    if llm_endpoint:
                                        docker_commands += f"""
      -e GOOGLE_API_ENDPOINT="{llm_endpoint}" \\"""
                                    if llm_provider and llm_provider != "auto":
                                        docker_commands += f"""
      -e LLM_PROVIDER="{llm_provider}" \\"""
                                    if llm_project:
                                        docker_commands += f"""
      -e GOOGLE_CLOUD_PROJECT="{llm_project}" \\"""
                                    
                                    docker_commands += f"""
      {docker_image_name}:{docker_tag}
    """
                                    
                                    if env_vars:
                                        env_lines = env_vars.strip().split("\\n")
                                        for env_line in env_lines:
                                            if "=" in env_line:
                                                docker_commands += f"  -e {env_line.strip()} \\\\\n"
                                    
                                    docker_commands = docker_commands.rstrip(" \\\n") + "\n"
                                    
                                    with st.expander("📋 Docker Commands"):
                                        st.code(docker_commands, language="bash")
                                    
                                    if st.button("📋 Copy Commands", key="copy_docker"):
                                        st.code(docker_commands, language="bash")
                                        st.success("Commands ready to copy!")
                                    
                                    # Quick deploy button (if docker is available)
                                    if st.button("🚀 Deploy Locally", type="primary", key="deploy_local"):
                                        st.info("""
    **To deploy locally:**
    1. Save the Dockerfile as `Dockerfile.agent`
    2. Run the docker commands shown above
    3. Or use: `python scripts/deploy_agent.py --agent {selected_agent} --target local`
                                        """)
                                
                                elif deployment_target == "GKE (Google)":
                                    st.subheader("☸️ GKE (Google Kubernetes Engine) Deployment")
                                    
                                    # Deployment mode: Build & push vs Deploy only (existing image)
                                    gke_mode = st.radio(
                                        "Deployment mode",
                                        ["Build image & push to Artifact Registry / GCR, then deploy", "Deploy only (image already in registry)"],
                                        key="gke_deploy_mode",
                                        horizontal=True,
                                        help="Build and push triggers a Kaniko job in-cluster; or use an existing image and only deploy."
                                    )
                                    
                                    gcr_image_url_final = None
                                    
                                    if gke_mode == "Build image & push to Artifact Registry / GCR, then deploy":
                                        st.markdown("### Step 1: Build and Push Docker Image")
                                        st.caption("Enter the Artifact Registry (or GCR) path where the built image will be pushed. When you click Build & Push, a Kaniko job runs in the cluster (if control-plane is in-cluster).")
                                        agent_version = agent_details.get("version", "1.0.0") if agent_details else "1.0.0"
                                        col_gcr1, col_gcr2 = st.columns(2)
                                        with col_gcr1:
                                            ar_path_gke = st.text_input(
                                                "Artifact Registry path to push the image to",
                                                value=st.session_state.get("gke_ar_path", ""),
                                                placeholder=f"us-central1-docker.pkg.dev/PROJECT/ravp-agents/agent-{selected_agent.lower()} or gcr.io/PROJECT/agent-{selected_agent.lower()}",
                                                key="gke_ar_path_input",
                                                help="Full path (repository + image name, without tag), e.g. us-central1-docker.pkg.dev/PROJECT/ravp-agents/agent-NAME or gcr.io/PROJECT/agent-NAME"
                                            )
                                            gcr_image_tag = st.text_input(
                                                "Image Tag",
                                                value=agent_version,
                                                key="gcr_tag",
                                                help="Agent version (used as image tag)."
                                            )
                                        with col_gcr2:
                                            if ar_path_gke:
                                                gcr_image_url = f"{ar_path_gke.rstrip(':')}:{gcr_image_tag}"
                                                st.caption(f"**Image URL (will be pushed):**\n`{gcr_image_url}`")
                                        
                                        if st.button("🔨 Build & Push Image", key="build_gcr"):
                                            if not ar_path_gke:
                                                st.error("Please enter Artifact Registry path to push the image to")
                                            else:
                                                gcr_image_url = f"{ar_path_gke.rstrip(':')}:{gcr_image_tag}"
                                                with st.spinner("Building and pushing image (Kaniko job in cluster)..."):
                                                    try:
                                                        r_build = requests.post(
                                                            f"{API_BASE_URL}/api/v2/docker/build-and-push",
                                                            headers=headers,
                                                            json={
                                                                "agent_id": selected_agent,
                                                                "registry_url": gcr_image_url,
                                                                "tag": gcr_image_tag
                                                            },
                                                            timeout=600
                                                        )
                                                        if r_build.status_code == 200:
                                                            result = r_build.json()
                                                            if result.get("success"):
                                                                st.session_state[f"gcr_image_{selected_agent}"] = result.get("image_url")
                                                                st.session_state["gke_ar_path"] = ar_path_gke
                                                                st.success(f"✅ Image pushed: {result.get('image_url')}")
                                                                st.rerun()
                                                            else:
                                                                err_msg = result.get("error") or ""
                                                                st.error(f"Build failed: {err_msg}")
                                                                if err_msg and ("403" in err_msg or "forbidden" in err_msg.lower() or "configmaps" in err_msg.lower()):
                                                                    st.info("💡 **Fix:** Apply build RBAC: `kubectl apply -f deploy/gke/kubernetes/control-plane-rbac-builds.yaml`")
                                                    except Exception as e:
                                                        st.error(f"Build error: {e}")
                                        
                                        if st.session_state.get(f"gcr_image_{selected_agent}"):
                                            gcr_image_url_final = st.session_state[f"gcr_image_{selected_agent}"]
                                            st.info(f"📦 Image ready: `{gcr_image_url_final}`")
                                    else:
                                        st.markdown("### Step 1: Use Existing Image")
                                        gcr_image_url_final = st.text_input(
                                            "Existing image URL",
                                            value=st.session_state.get(f"gcr_image_{selected_agent}") or f"us-central1-docker.pkg.dev/PROJECT/ravp-agents/agent-{selected_agent.lower()}:latest",
                                            key="gke_existing_image",
                                            help="Full image URL already in Artifact Registry or GCR (e.g. us-central1-docker.pkg.dev/PROJECT/ravp-agents/agent-NAME:1.0.0 or gcr.io/PROJECT/agent-NAME:latest)"
                                        )
                                        if gcr_image_url_final and "YOUR_PROJECT" not in gcr_image_url_final:
                                            st.caption("You can proceed to Step 2 to configure and record the deployment.")
                                    
                                    st.markdown("### Step 2: Configure and Deploy")
                                    
                                    st.markdown("#### Cluster and deployment config")
                                    col_gke_cluster1, col_gke_cluster2 = st.columns(2)
                                    with col_gke_cluster1:
                                        gke_project = st.text_input("GCP Project ID", value=st.session_state.get("gke_project") or "", key="gke_project", help="Project that owns the GKE cluster")
                                        gke_cluster_name = st.text_input("GKE Cluster name", value="", key="gke_cluster_name", help="Name of the cluster (e.g. my-agent-cluster)")
                                        gke_location = st.text_input("Region or zone", value="", key="gke_location", placeholder="e.g. us-central1 or us-central1-a", help="Region (us-central1) or zone (us-central1-a) for the cluster")
                                    with col_gke_cluster2:
                                        gke_namespace = st.text_input("Namespace", value="agents", key="gke_ns", help="Kubernetes namespace to deploy into")
                                        image_for_deploy = st.text_input("Container image", value=gcr_image_url_final or f"gcr.io/PROJECT/agent-{selected_agent.lower()}:latest", key="gke_image_input")
                                        control_plane_url_gke = st.text_input("Control Plane URL", value="http://control-plane:8010", key="gke_cp_url", help="URL the agent uses to reach the control plane")
                                        gke_port = st.number_input("Port", value=8080, min_value=1000, max_value=65535, key="gke_port")
                                    gke_env = st.text_input("Environment name", value="gke-prod", key="gke_env", help="Logical environment for this deployment record (e.g. gke-prod, gke-dev)")
                                    
                                    # Kubernetes manifest
                                    dockerfile_content_gke = f"""FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY agents/{selected_agent}/ ./agents/{selected_agent}/
    COPY agent-sdk/ ./agent-sdk/
    COPY config/ ./config/
    ENV CONTROL_PLANE_URL={control_plane_url_gke}
    ENV PYTHONPATH=/app
    EXPOSE {gke_port}
    CMD ["python", "-m", "agents.{selected_agent}.agent"]
    """
                                    k8s_name = selected_agent.replace("_", "-").lower()
                                    deployment_manifest_gke = textwrap.dedent(f"""\
                                    apiVersion: apps/v1
                                    kind: Deployment
                                    metadata:
                                      name: {k8s_name}
                                      namespace: {gke_namespace}
                                      labels:
                                        app: {k8s_name}
                                        component: agent
                                    spec:
                                      replicas: 1
                                      selector:
                                        matchLabels:
                                          app: {k8s_name}
                                      template:
                                        metadata:
                                          labels:
                                            app: {k8s_name}
                                        spec:
                                          containers:
                                          - name: {k8s_name}
                                            image: {image_for_deploy}
                                            ports:
                                            - containerPort: {gke_port}
                                            env:
                                            - name: CONTROL_PLANE_URL
                                              value: "{control_plane_url_gke}"
                                            - name: GOOGLE_API_KEY
                                              valueFrom:
                                                secretKeyRef:
                                                  name: agent-secrets
                                                  key: google-api-key
                                            resources:
                                              requests:
                                                cpu: "100m"
                                                memory: "256Mi"
                                              limits:
                                                cpu: "500m"
                                                memory: "512Mi"
                                    ---
                                    apiVersion: v1
                                    kind: Service
                                    metadata:
                                      name: {k8s_name}
                                      namespace: {gke_namespace}
                                    spec:
                                      type: ClusterIP
                                      ports:
                                      - port: 80
                                        targetPort: {gke_port}
                                        selector:
                                          app: {k8s_name}
                                    """)
                                    with st.expander("📄 Deployment YAML (for kubectl apply)"):
                                        st.code(deployment_manifest_gke, language="yaml")
                                        st.download_button("📥 Download YAML", data=deployment_manifest_gke, file_name=f"{selected_agent}-gke.yaml", mime="text/yaml", key="dl_gke_yaml")
                                    
                                    # LLM Configuration Section (right before deploy button)
                                    st.divider()
                                    st.markdown("#### 🤖 LLM Configuration (Runtime)")
                                    st.caption("Configure which LLM service this deployment will use at runtime")
                                    
                                    with st.expander("ℹ️ Why configure LLM at deployment?", expanded=False):
                                        st.markdown("""
**Benefits:**
- 🔄 **Flexibility**: Same agent image, different LLM backends per environment  
- 🔒 **Security**: API keys passed at deployment, not baked into code  
- 🏢 **Multi-tenant**: Each deployment can use different endpoints  
- 🧪 **Easy testing**: Dev uses AI Studio, Prod uses Vertex AI

**Common Scenarios:**
- **Dev**: Google AI Studio with simple API key
- **Staging**: Corporate Vertex AI for testing
- **Prod**: Production Vertex AI with regional endpoints
                                        """)
                                    
                                    llm_col1, llm_col2 = st.columns(2)
                                    with llm_col1:
                                        gke_api_key_deploy = st.text_input("API Key", type="password",
                                            help="LLM API key (passed securely as env var)", key="gke_deploy_api_key")
                                        gke_llm_provider_deploy = st.selectbox("Provider", 
                                            ["auto", "google", "vertex_ai", "openai", "anthropic"],
                                            help="Leave as 'auto' to auto-detect from model", key="gke_deploy_provider")
                                    with llm_col2:
                                        gke_llm_endpoint_deploy = st.text_input("Custom Endpoint (optional)",
                                            placeholder="https://vertex-api.yourcompany.com",
                                            help="For Vertex AI, corporate proxy, etc.", key="gke_deploy_endpoint")
                                        gke_llm_project_deploy = st.text_input("GCP Project for LLM (optional)",
                                            placeholder="your-gcp-project",
                                            help="For Vertex AI provider", key="gke_deploy_llm_project")
                                    
                                    st.divider()
                                    
                                    col_deploy_gke, col_cancel_gke = st.columns(2)
                                    with col_deploy_gke:
                                        if st.button("🚀 Deploy", type="primary", key="deploy_gke"):
                                            if not image_for_deploy or "PROJECT" in image_for_deploy:
                                                st.error("Please set a valid container image URL.")
                                            elif not gke_project or not gke_cluster_name:
                                                st.error("Please set GCP Project ID and GKE Cluster name.")
                                            else:
                                                try:
                                                    # 1. Deploy to GKE: get credentials and apply manifest
                                                    r_gke = requests.post(
                                                        f"{API_BASE_URL}/api/v2/gke/deploy",
                                                        headers=headers,
                                                        json={
                                                            "gcp_project": gke_project,
                                                            "gke_cluster": gke_cluster_name,
                                                            "gke_location": gke_location.strip() or None,
                                                            "manifest_yaml": deployment_manifest_gke,
                                                        },
                                                        timeout=180,
                                                    )
                                                    if r_gke.status_code != 200:
                                                        err = r_gke.json().get("detail", r_gke.text) if r_gke.headers.get("content-type", "").startswith("application/json") else r_gke.text
                                                        st.error(f"Deploy failed: {err}")
                                                    else:
                                                        # 2. Record deployment in registry
                                                        deploy_payload = {
                                                            "agent_id": selected_agent,
                                                            "environment": gke_env,
                                                            "deployment_type": "gke",
                                                            "status": "deployed",
                                                            "endpoint": f"http://{k8s_name}.{gke_namespace}.svc.cluster.local",
                                                            "image_url": image_for_deploy,
                                                            "metadata": {
                                                                "image_url": image_for_deploy,
                                                                "namespace": gke_namespace,
                                                                "control_plane_url": control_plane_url_gke,
                                                                "port": gke_port,
                                                                "gcp_project": gke_project,
                                                                "gke_cluster": gke_cluster_name,
                                                                "gke_location": gke_location.strip() or None,
                                                            },
                                                        }
                                                        r_dep = requests.post(f"{API_BASE_URL}/api/v2/deployments", headers=headers, json=deploy_payload, timeout=5)
                                                        if r_dep.status_code == 200:
                                                            st.success(f"✅ Deployed {selected_agent} to cluster {gke_cluster_name} (namespace: {gke_namespace}) and recorded in {gke_env}.")
                                                        else:
                                                            st.warning(f"Deployed to GKE but failed to record deployment: {r_dep.text}")
                                                except requests.exceptions.Timeout:
                                                    st.error("Deploy request timed out. Check control plane has gcloud and kubectl and access to the cluster.")
                                                except Exception as e:
                                                    st.error(str(e))
                                    
                                elif deployment_target == "AKS (Azure)":
                                    st.subheader("☸️ AKS (Azure Kubernetes Service) Deployment")
                                    
                                    aks_mode = st.radio(
                                        "Deployment mode",
                                        ["Build image & push to ACR, then deploy", "Deploy only (image already in ACR)"],
                                        key="aks_deploy_mode",
                                        horizontal=True,
                                    )
                                    
                                    acr_image_url_final = None
                                    if aks_mode == "Build image & push to ACR, then deploy":
                                        st.markdown("### Step 1: Build and Push Docker Image")
                                        col_acr1, col_acr2 = st.columns(2)
                                        with col_acr1:
                                            acr_name = st.text_input("ACR Registry Name", key="acr_name", help="Your Azure Container Registry name")
                                            acr_image_tag = st.text_input("Image Tag", value="latest", key="acr_tag")
                                        with col_acr2:
                                            if acr_name:
                                                acr_image_url = f"{acr_name}.azurecr.io/agent-{selected_agent.lower()}:{acr_image_tag}"
                                                st.caption(f"**Image URL:**\n`{acr_image_url}`")
                                        
                                        if st.button("🔨 Build & Push to ACR", key="build_acr"):
                                            if not acr_name:
                                                st.error("Please enter ACR Registry Name")
                                            else:
                                                with st.spinner("Building and pushing to ACR..."):
                                                    try:
                                                        r_build = requests.post(
                                                            f"{API_BASE_URL}/api/v2/docker/build-and-push",
                                                            headers=headers,
                                                            json={
                                                                "agent_id": selected_agent,
                                                                "registry_url": acr_image_url,
                                                                "tag": acr_image_tag
                                                            },
                                                            timeout=600
                                                        )
                                                        if r_build.status_code == 200:
                                                            result = r_build.json()
                                                            if result.get("success"):
                                                                st.success(f"✅ Image pushed: {result.get('image_url')}")
                                                                st.session_state[f"acr_image_{selected_agent}"] = result.get("image_url")
                                                                st.rerun()
                                                            else:
                                                                st.error(f"Build failed: {result.get('error')}")
                                                    except Exception as e:
                                                        st.error(f"Build error: {e}")
                                        
                                        if st.session_state.get(f"acr_image_{selected_agent}"):
                                            acr_image_url_final = st.session_state[f"acr_image_{selected_agent}"]
                                            st.info(f"📦 Image ready: `{acr_image_url_final}`")
                                    else:
                                        st.markdown("### Step 1: Use Existing Image")
                                        acr_image_url_final = st.text_input(
                                            "Existing image URL",
                                            value=st.session_state.get(f"acr_image_{selected_agent}") or f"YOUR_ACR.azurecr.io/agent-{selected_agent.lower()}:latest",
                                            key="aks_existing_image",
                                            help="Full image URL already in ACR"
                                        )
                                    
                                    st.markdown("### Step 2: Configure and Deploy")
                                    aks_env = st.text_input("Environment name", value="aks-prod", key="aks_env")
                                    aks_namespace = st.text_input("Namespace", value="agents", key="aks_ns")
                                    aks_image_for_deploy = st.text_input("Container image", value=acr_image_url_final or f"YOUR_ACR.azurecr.io/agent-{selected_agent.lower()}:latest", key="aks_image_input")
                                    aks_cp_url = st.text_input("Control Plane URL", value="http://control-plane:8010", key="aks_cp_url")
                                    aks_port = st.number_input("Port", value=8080, min_value=1000, max_value=65535, key="aks_port")
                                    
                                    # LLM Configuration Section
                                    st.divider()
                                    st.markdown("#### 🤖 LLM Configuration (Runtime)")
                                    st.caption("Configure which LLM service this deployment will use")
                                    
                                    aks_llm_col1, aks_llm_col2 = st.columns(2)
                                    with aks_llm_col1:
                                        aks_api_key_deploy = st.text_input("API Key", type="password",
                                            help="LLM API key", key="aks_deploy_api_key")
                                        aks_llm_provider_deploy = st.selectbox("Provider", 
                                            ["auto", "google", "vertex_ai", "openai", "anthropic"],
                                            help="Leave as 'auto' to auto-detect", key="aks_deploy_provider")
                                    with aks_llm_col2:
                                        aks_llm_endpoint_deploy = st.text_input("Custom Endpoint (optional)",
                                            placeholder="https://your-endpoint.com",
                                            help="Custom LLM endpoint", key="aks_deploy_endpoint")
                                        aks_llm_project_deploy = st.text_input("GCP Project (optional)",
                                            placeholder="your-gcp-project",
                                            help="For Vertex AI", key="aks_deploy_project")
                                    
                                    st.divider()
                                    
                                    if st.button("🚀 Record deployment", type="primary", key="record_aks"):
                                        if not aks_image_for_deploy or "YOUR_ACR" in aks_image_for_deploy:
                                            st.error("Please set a valid container image URL.")
                                        else:
                                            try:
                                                deploy_payload = {
                                                    "agent_id": selected_agent,
                                                    "environment": aks_env,
                                                    "deployment_type": "aks",
                                                    "status": "deployed",
                                                    "endpoint": f"http://{selected_agent}.{aks_namespace}.svc.cluster.local",
                                                    "image_url": aks_image_for_deploy,
                                                    "metadata": {"image_url": aks_image_for_deploy, "namespace": aks_namespace, "control_plane_url": aks_cp_url, "port": aks_port}
                                                }
                                                r_dep = requests.post(f"{API_BASE_URL}/api/v2/deployments", headers=headers, json=deploy_payload, timeout=5)
                                                if r_dep.status_code == 200:
                                                    st.success(f"✅ Deployment recorded for {selected_agent} in {aks_env}.")
                                                else:
                                                    st.error(r_dep.text or "Failed to record deployment")
                                            except Exception as e:
                                                st.error(str(e))
                                    
                                elif deployment_target == "EKS (AWS)":
                                    st.subheader("☸️ EKS (Amazon Elastic Kubernetes Service) Deployment")
                                    
                                    eks_mode = st.radio(
                                        "Deployment mode",
                                        ["Build image & push to ECR, then deploy", "Deploy only (image already in ECR)"],
                                        key="eks_deploy_mode",
                                        horizontal=True,
                                    )
                                    
                                    ecr_image_url_final = None
                                    if eks_mode == "Build image & push to ECR, then deploy":
                                        st.markdown("### Step 1: Build and Push Docker Image")
                                        col_ecr1, col_ecr2 = st.columns(2)
                                        with col_ecr1:
                                            ecr_account = st.text_input("AWS Account ID", key="ecr_account", help="Your AWS account ID")
                                            ecr_region = st.text_input("AWS Region", value="us-east-1", key="ecr_region", help="ECR region")
                                            ecr_image_tag = st.text_input("Image Tag", value="latest", key="ecr_tag")
                                        with col_ecr2:
                                            if ecr_account and ecr_region:
                                                ecr_image_url = f"{ecr_account}.dkr.ecr.{ecr_region}.amazonaws.com/agent-{selected_agent.lower()}:{ecr_image_tag}"
                                                st.caption(f"**Image URL:**\n`{ecr_image_url}`")
                                        
                                        if st.button("🔨 Build & Push to ECR", key="build_ecr"):
                                            if not ecr_account or not ecr_region:
                                                st.error("Please enter AWS Account ID and Region")
                                            else:
                                                with st.spinner("Building and pushing to ECR..."):
                                                    try:
                                                        r_build = requests.post(
                                                            f"{API_BASE_URL}/api/v2/docker/build-and-push",
                                                            headers=headers,
                                                            json={
                                                                "agent_id": selected_agent,
                                                                "registry_url": ecr_image_url,
                                                                "tag": ecr_image_tag
                                                            },
                                                            timeout=600
                                                        )
                                                        if r_build.status_code == 200:
                                                            result = r_build.json()
                                                            if result.get("success"):
                                                                st.success(f"✅ Image pushed: {result.get('image_url')}")
                                                                st.session_state[f"ecr_image_{selected_agent}"] = result.get("image_url")
                                                                st.rerun()
                                                            else:
                                                                st.error(f"Build failed: {result.get('error')}")
                                                    except Exception as e:
                                                        st.error(f"Build error: {e}")
                                        
                                        if st.session_state.get(f"ecr_image_{selected_agent}"):
                                            ecr_image_url_final = st.session_state[f"ecr_image_{selected_agent}"]
                                            st.info(f"📦 Image ready: `{ecr_image_url_final}`")
                                    else:
                                        st.markdown("### Step 1: Use Existing Image")
                                        ecr_image_url_final = st.text_input(
                                            "Existing image URL",
                                            value=st.session_state.get(f"ecr_image_{selected_agent}") or f"ACCOUNT.dkr.ecr.REGION.amazonaws.com/agent-{selected_agent.lower()}:latest",
                                            key="eks_existing_image",
                                            help="Full image URL already in ECR"
                                        )
                                    
                                    st.markdown("### Step 2: Configure and Deploy")
                                    eks_env = st.text_input("Environment name", value="eks-prod", key="eks_env")
                                    eks_namespace = st.text_input("Namespace", value="agents", key="eks_ns")
                                    eks_image_for_deploy = st.text_input("Container image", value=ecr_image_url_final or f"ACCOUNT.dkr.ecr.REGION.amazonaws.com/agent-{selected_agent.lower()}:latest", key="eks_image_input")
                                    eks_cp_url = st.text_input("Control Plane URL", value="http://control-plane:8010", key="eks_cp_url")
                                    eks_port = st.number_input("Port", value=8080, min_value=1000, max_value=65535, key="eks_port")
                                    
                                    # LLM Configuration Section
                                    st.divider()
                                    st.markdown("#### 🤖 LLM Configuration (Runtime)")
                                    st.caption("Configure which LLM service this deployment will use")
                                    
                                    eks_llm_col1, eks_llm_col2 = st.columns(2)
                                    with eks_llm_col1:
                                        eks_api_key_deploy = st.text_input("API Key", type="password",
                                            help="LLM API key", key="eks_deploy_api_key")
                                        eks_llm_provider_deploy = st.selectbox("Provider", 
                                            ["auto", "google", "vertex_ai", "openai", "anthropic"],
                                            help="Leave as 'auto' to auto-detect", key="eks_deploy_provider")
                                    with eks_llm_col2:
                                        eks_llm_endpoint_deploy = st.text_input("Custom Endpoint (optional)",
                                            placeholder="https://your-endpoint.com",
                                            help="Custom LLM endpoint", key="eks_deploy_endpoint")
                                        eks_llm_project_deploy = st.text_input("GCP Project (optional)",
                                            placeholder="your-gcp-project",
                                            help="For Vertex AI", key="eks_deploy_project")
                                    
                                    st.divider()
                                    
                                    if st.button("🚀 Record deployment", type="primary", key="record_eks"):
                                        if not eks_image_for_deploy or "ACCOUNT" in eks_image_for_deploy or "REGION" in eks_image_for_deploy:
                                            st.error("Please set a valid container image URL.")
                                        else:
                                            try:
                                                deploy_payload = {
                                                    "agent_id": selected_agent,
                                                    "environment": eks_env,
                                                    "deployment_type": "eks",
                                                    "status": "deployed",
                                                    "endpoint": f"http://{selected_agent}.{eks_namespace}.svc.cluster.local",
                                                    "image_url": eks_image_for_deploy,
                                                    "metadata": {"image_url": eks_image_for_deploy, "namespace": eks_namespace, "control_plane_url": eks_cp_url, "port": eks_port}
                                                }
                                                r_dep = requests.post(f"{API_BASE_URL}/api/v2/deployments", headers=headers, json=deploy_payload, timeout=5)
                                                if r_dep.status_code == 200:
                                                    st.success(f"✅ Deployment recorded for {selected_agent} in {eks_env}.")
                                                else:
                                                    st.error(r_dep.text or "Failed to record deployment")
                                            except Exception as e:
                                                st.error(str(e))
                                    
                                else:  # GKE deployment (fallback for existing code)
                                    st.subheader("☸️ GKE (Google Kubernetes Engine) Deployment")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        gke_project = st.text_input("GCP Project ID", help="Your GCP project ID")
                                        gke_cluster = st.text_input("GKE Cluster Name", help="Name of your GKE cluster")
                                        gke_namespace = st.text_input("Namespace", value="agents", help="Kubernetes namespace")
                                        gke_replicas = st.number_input("Replicas", value=1, min_value=1, max_value=10)
                                    
                                    with col2:
                                        gke_image = st.text_input("Container Image", 
                                            value=f"gcr.io/{gke_project}/agent-{selected_agent.lower()}:latest",
                                            help="Full container image path")
                                        control_plane_url_gke = st.text_input("Control Plane URL", 
                                            value="http://control-plane:8010",
                                            help="Control plane service URL in cluster")
                                        gke_port = st.number_input("Port", value=8080, min_value=1000, max_value=65535)
                                    
                                    # Resource requests
                                    st.subheader("Resource Configuration")
                                    res_col1, res_col2 = st.columns(2)
                                    with res_col1:
                                        cpu_request = st.text_input("CPU Request", value="100m", help="e.g., 100m, 0.5, 1")
                                        memory_request = st.text_input("Memory Request", value="256Mi", help="e.g., 256Mi, 512Mi, 1Gi")
                                    with res_col2:
                                        cpu_limit = st.text_input("CPU Limit", value="500m", help="e.g., 500m, 1, 2")
                                        memory_limit = st.text_input("Memory Limit", value="512Mi", help="e.g., 512Mi, 1Gi, 2Gi")
                                    
                                    # LLM Configuration Section for GKE
                                    st.divider()
                                    st.subheader("🤖 LLM Configuration (Runtime)")
                                    st.caption("Configure which LLM service this deployment should use")
                                    
                                    with st.expander("ℹ️ About Runtime LLM Configuration"):
                                        st.markdown("""
**Why configure LLM at deployment time?**

- **Flexibility**: Same agent can use different LLM services per environment
- **Security**: Keep API keys out of agent definitions
- **Multi-tenant**: Different deployments can use different endpoints
- **Easy testing**: Switch between AI Studio (dev) and Vertex AI (prod)

**Examples:**
- **Development**: Use Google AI Studio with a simple API key
- **Production**: Use Vertex AI with your corporate endpoint
- **Multi-region**: Deploy to different regions with regional endpoints
                                        """)
                                    
                                    llm_config_option = st.radio("LLM Configuration Method", 
                                        ["Use Kubernetes Secret (Recommended)", "Provide API Key Directly"],
                                        help="Choose how to provide LLM credentials")
                                    
                                    gke_llm_col1, gke_llm_col2 = st.columns(2)
                                    with gke_llm_col1:
                                        if llm_config_option == "Provide API Key Directly":
                                            gke_api_key = st.text_input("API Key", type="password",
                                                help="API key for LLM access", key="gke_api_key")
                                        else:
                                            gke_secret_name = st.text_input("Secret Name", value="agent-secrets",
                                                help="Name of Kubernetes secret containing API key", key="gke_secret_name")
                                            gke_secret_key = st.text_input("Secret Key", value="google-api-key",
                                                help="Key within the secret", key="gke_secret_key")
                                        
                                        gke_llm_provider = st.selectbox("Provider (optional)", 
                                            ["auto", "google", "vertex_ai", "openai", "anthropic"],
                                            help="Leave as 'auto' to detect from model name", key="gke_provider")
                                    
                                    with gke_llm_col2:
                                        gke_llm_endpoint = st.text_input("Custom Endpoint (optional)",
                                            placeholder="https://your-vertex-endpoint.com",
                                            help="Custom endpoint for Vertex AI, corporate proxy, etc.", key="gke_endpoint")
                                        gke_llm_project = st.text_input("GCP Project (for Vertex AI, optional)",
                                            placeholder="your-gcp-project",
                                            help="Required for Vertex AI provider", key="gke_llm_project")
                                    
                                    st.markdown("### Kubernetes Manifests")
                                    
                                    # Build env vars for manifest
                                    env_vars_yaml = f"""            - name: CONTROL_PLANE_URL
              value: "{control_plane_url_gke}"
"""
                                    # LLM API Key
                                    if llm_config_option == "Provide API Key Directly" and 'gke_api_key' in locals() and gke_api_key:
                                        env_vars_yaml += f"""            - name: GOOGLE_API_KEY
              value: "{gke_api_key}"
"""
                                    else:
                                        secret_name = gke_secret_name if 'gke_secret_name' in locals() and gke_secret_name else "agent-secrets"
                                        secret_key = gke_secret_key if 'gke_secret_key' in locals() and gke_secret_key else "google-api-key"
                                        env_vars_yaml += f"""            - name: GOOGLE_API_KEY
              valueFrom:
                secretKeyRef:
                  name: {secret_name}
                  key: {secret_key}
"""
                                    # LLM Endpoint
                                    if 'gke_llm_endpoint' in locals() and gke_llm_endpoint:
                                        env_vars_yaml += f"""            - name: GOOGLE_API_ENDPOINT
              value: "{gke_llm_endpoint}"
"""
                                    # LLM Provider
                                    if 'gke_llm_provider' in locals() and gke_llm_provider and gke_llm_provider != "auto":
                                        env_vars_yaml += f"""            - name: LLM_PROVIDER
              value: "{gke_llm_provider}"
"""
                                    # GCP Project
                                    if 'gke_llm_project' in locals() and gke_llm_project:
                                        env_vars_yaml += f"""            - name: GOOGLE_CLOUD_PROJECT
              value: "{gke_llm_project}"
"""
                                    
                                    # Generate Deployment manifest
                                    deployment_manifest = f"""apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: {selected_agent}
      namespace: {gke_namespace}
      labels:
        app: {selected_agent}
        component: agent
    spec:
      replicas: {gke_replicas}
      selector:
        matchLabels:
          app: {selected_agent}
      template:
        metadata:
          labels:
            app: {selected_agent}
        spec:
          containers:
          - name: {selected_agent}
            image: {gke_image}
            ports:
            - containerPort: {gke_port}
            env:
{env_vars_yaml}            resources:
              requests:
                cpu: {cpu_request}
                memory: {memory_request}
              limits:
                cpu: {cpu_limit}
                memory: {memory_limit}
            livenessProbe:
              httpGet:
                path: /health
                port: {gke_port}
              initialDelaySeconds: 30
              periodSeconds: 10
            readinessProbe:
              httpGet:
                path: /health
                port: {gke_port}
              initialDelaySeconds: 10
              periodSeconds: 5
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: {selected_agent}
      namespace: {gke_namespace}
      labels:
        app: {selected_agent}
    spec:
      type: ClusterIP
      ports:
      - port: 80
        targetPort: {gke_port}
        protocol: TCP
      selector:
        app: {selected_agent}
    """
                                    
                                    with st.expander("📄 Deployment Manifest"):
                                        st.code(deployment_manifest, language="yaml")
                                    
                                    # Generate deployment commands
                                    secret_cmds = ""
                                    if llm_config_option != "Provide API Key Directly":
                                        secret_name = gke_secret_name if 'gke_secret_name' in locals() and gke_secret_name else "agent-secrets"
                                        secret_key = gke_secret_key if 'gke_secret_key' in locals() and gke_secret_key else "google-api-key"
                                        secret_cmds = f"""# Create secret for API keys (if not exists)
    kubectl create secret generic {secret_name} \\
      --from-literal={secret_key}="$GOOGLE_API_KEY" \\
      --namespace={gke_namespace} \\
      --dry-run=client -o yaml | kubectl apply -f -
    """
                                    
                                    gke_commands = f"""# Set GCP project and cluster
    gcloud config set project {gke_project}
    gcloud container clusters get-credentials {gke_cluster}
    
    # Create namespace (if not exists)
    kubectl create namespace {gke_namespace} --dry-run=client -o yaml | kubectl apply -f -
    
    {secret_cmds}
    
    # Build and push Docker image
    docker build -t {gke_image} -f Dockerfile.agent .
    docker push {gke_image}
    
    # Deploy to GKE
    kubectl apply -f deployment.yaml
    
    # Check deployment status
    kubectl get pods -n {gke_namespace} -l app={selected_agent}
    kubectl logs -n {gke_namespace} -l app={selected_agent} --tail=50
    """
                                    
                                    with st.expander("📋 GKE Deployment Commands"):
                                        st.code(gke_commands, language="bash")
                                    
                                    # Download buttons
                                    col_dl1, col_dl2 = st.columns(2)
                                    with col_dl1:
                                        st.download_button(
                                            label="📥 Download Deployment YAML",
                                            data=deployment_manifest,
                                            file_name=f"{selected_agent}-deployment.yaml",
                                            mime="text/yaml"
                                        )
                                    
                                    with col_dl2:
                                        st.download_button(
                                            label="📥 Download Dockerfile",
                                            data=dockerfile_content,
                                            file_name=f"Dockerfile.{selected_agent}",
                                            mime="text/plain"
                                        )
                                    
                                    if st.button("📋 Copy Commands", key="copy_gke"):
                                        st.code(gke_commands, language="bash")
                                        st.success("Commands ready to copy!")
                                    
                                    # Deployment status check
                                    st.divider()
                                    st.subheader("Deployment Status")
                                    if st.button("🔍 Check Deployment Status", key="check_status"):
                                        st.info(f"""
    **To check deployment status:**
    ```bash
    kubectl get pods -n {gke_namespace} -l app={selected_agent}
    kubectl describe pod -n {gke_namespace} -l app={selected_agent}
    kubectl logs -n {gke_namespace} -l app={selected_agent} --tail=100
    ```
                                        """)
                        except Exception as e:
                            st.error(f"Could not load agent details: {e}")
    
        with tab5:
            st.header("📦 Deployed Agents")
            st.caption("View and interact with agents deployed across environments")
            
            if not st.session_state.logged_in:
                st.warning("Please log in to view deployed agents.")
            else:
                try:
                    # Get all deployments
                    r_deployments = requests.get(f"{API_BASE_URL}/api/v2/deployments", headers=headers, timeout=3)
                    if r_deployments.status_code == 200:
                        all_deployments = r_deployments.json().get("deployments", [])
                        
                        if all_deployments:
                            # Group by environment
                            by_env = {}
                            for dep in all_deployments:
                                env = dep.get("environment", "unknown")
                                if env not in by_env:
                                    by_env[env] = []
                                by_env[env].append(dep)
                            
                            # Show deployments by environment
                            for env_name, deployments in sorted(by_env.items()):
                                with st.expander(f"🌍 {env_name.upper()} ({len(deployments)} agents)", expanded=True):
                                    for dep in deployments:
                                        agent_id = dep.get("agent_id", "")
                                        status = dep.get("status", "unknown")
                                        deploy_type = dep.get("deployment_type", "unknown")
                                        endpoint = dep.get("endpoint", "")
                                        updated_at = dep.get("updated_at", "")
                                        
                                        # Status indicators
                                        if status == "running":
                                            status_badge = "🟢 Running"
                                        elif status == "deployed":
                                            status_badge = "🟡 Deployed"
                                        elif status == "stopped":
                                            status_badge = "⚪ Stopped"
                                        elif status == "failed":
                                            status_badge = "🔴 Failed"
                                        else:
                                            status_badge = f"❓ {status}"
                                        
                                        col_dep1, col_dep2, col_dep3 = st.columns([3, 2, 1])
                                        with col_dep1:
                                            st.write(f"**{agent_id}**")
                                            st.caption(f"Type: {deploy_type} | {status_badge}")
                                            if endpoint:
                                                st.caption(f"Endpoint: {endpoint}")
                                            if updated_at:
                                                st.caption(f"Updated: {updated_at[:19]}")
                                        
                                        with col_dep2:
                                            # Show agent version
                                            try:
                                                r_agent = requests.get(
                                                    f"{API_BASE_URL}/agents/{agent_id}",
                                                    headers=headers,
                                                    timeout=2
                                                )
                                                if r_agent.status_code == 200:
                                                    agent_def = r_agent.json()
                                                    version = agent_def.get("version", "N/A")
                                                    st.caption(f"Version: {version}")
                                            except Exception:
                                                pass
                                        
                                        with col_dep3:
                                            if status == "running":
                                                if st.button(f"💬 Interact", key=f"interact_deployed_{agent_id}_{env_name}"):
                                                    st.session_state[f"interacting_deployed_{agent_id}_{env_name}"] = True
                                                    st.rerun()
                                                
                                                if st.session_state.get(f"interacting_deployed_{agent_id}_{env_name}"):
                                                    st.divider()
                                                    st.subheader(f"Interact with {agent_id} ({env_name})")
                                                    query = st.text_input("Enter your query:", key=f"query_deployed_{agent_id}_{env_name}")
                                                    
                                                    col_send1, col_send2 = st.columns(2)
                                                    with col_send1:
                                                        if st.button("Send Query", key=f"send_deployed_{agent_id}_{env_name}"):
                                                            st.info("💡 Agent interaction would happen here via agent SDK or API")
                                                            st.code(f"""
    from org_agent_sdk.agent import RegulatedAgent
    
    agent = RegulatedAgent(agent_id="{agent_id}")
    result = agent.invoke("{query}")
    print(result)
                                                            """)
                                                            if endpoint:
                                                                st.caption(f"Or via HTTP: POST {endpoint}/invoke")
                                                    
                                                    with col_send2:
                                                        if st.button("Close", key=f"close_interact_{agent_id}_{env_name}"):
                                                            st.session_state[f"interacting_deployed_{agent_id}_{env_name}"] = False
                                                            st.rerun()
                                            
                                            # Update status button
                                            if st.button("🔄 Update", key=f"update_status_{agent_id}_{env_name}"):
                                                st.session_state[f"updating_status_{agent_id}_{env_name}"] = True
                                                st.rerun()
                                            
                                            if st.session_state.get(f"updating_status_{agent_id}_{env_name}"):
                                                new_status = st.selectbox(
                                                    "Status",
                                                    ["running", "deployed", "stopped", "failed"],
                                                    index=["running", "deployed", "stopped", "failed"].index(status) if status in ["running", "deployed", "stopped", "failed"] else 0,
                                                    key=f"new_status_{agent_id}_{env_name}"
                                                )
                                                if st.button("Save", key=f"save_status_{agent_id}_{env_name}"):
                                                    try:
                                                        r_update = requests.put(
                                                            f"{API_BASE_URL}/api/v2/deployments/{agent_id}/{env_name}",
                                                            headers=headers,
                                                            json={"status": new_status},
                                                            timeout=3
                                                        )
                                                        if r_update.status_code == 200:
                                                            st.success("Status updated")
                                                            st.session_state[f"updating_status_{agent_id}_{env_name}"] = False
                                                            st.rerun()
                                                    except Exception as e:
                                                        st.error(f"Failed to update: {e}")
                                        
                                        st.divider()
                        else:
                            st.info("No deployments found. Deploy agents from the 'Browse Agents' or 'Deploy Agent' tab.")
                    elif r_deployments.status_code == 401:
                        st.warning("Please log in to view deployments.")
                    else:
                        st.error(f"Error {r_deployments.status_code}: {r_deployments.text}")
                except Exception as e:
                    st.warning(f"API not reachable: {e}")
                
                # Multi-tenancy info
                st.divider()
                st.subheader("ℹ️ About Multi-Tenancy")
                st.info("""
                **Yes, agents can serve multiple users simultaneously!**
                
                - Each deployed agent instance can handle multiple concurrent requests
                - Users can interact with the same agent independently
                - Each request is isolated and processed separately
                - Agent state is typically stateless (each invocation is independent)
                
                **How it works:**
                1. Deploy agent to an environment (local, GKE, Cloud Run, etc.)
                2. Multiple users can send queries to the same deployed agent
                3. Each query is processed independently
                4. Responses are returned to the respective users
                
                **Example:**
                - User A queries: "What is payment exception X?"
                - User B queries: "Retry payment Y" (at the same time)
                - Both queries are processed concurrently by the same agent instance
                """)
    
        with tab6:
            st.header("🛠️ Manage Tools")
            if not is_admin:
                st.warning("Log in as **admin@platform.com** to manage tools. Then refresh or re-run.")
            else:
                try:
                    # ---------- Create new tool (template: API-based or metadata-only) ----------
                    with st.expander("➕ Create new tool", expanded=st.session_state.get("create_tool_expanded", False)):
                        st.caption("Tools can be **API-based** (call an existing HTTP API at runtime) or **metadata-only** (register for governance; implementation in code).")
                        template = st.radio(
                            "Template",
                            ["API-based tool (call existing API)", "Metadata only (register only; implementation in code)"],
                            key="tool_template",
                            horizontal=True,
                        )
                        tool_id = st.text_input("Tool ID", key="new_tool_id", placeholder="e.g. get_order_details", help="Unique name for the tool")
                        domain = st.text_input("Domain (comma-separated)", value="general", key="new_tool_domain", placeholder="e.g. payments, customer, general", help="One or more domains, comma-separated; the first is used for storage.")
                        description = st.text_area("Description", key="new_tool_desc", height=80, placeholder="What this tool does (for agents and governance)")
                        col1, col2 = st.columns(2)
                        with col1:
                            data_sources = st.text_input("Data sources (comma-separated)", key="new_tool_ds", placeholder="e.g. OrderService, PaymentGateway")
                            pii_level = st.selectbox("PII level", ["none", "low", "medium", "high"], key="new_tool_pii")
                        with col2:
                            risk_tier = st.selectbox("Risk tier", ["low", "medium", "high"], key="new_tool_risk")
                            requires_human = st.checkbox("Requires human approval", key="new_tool_human")
    
                        if template == "API-based tool (call existing API)":
                            st.subheader("API configuration")
                            st.caption("The tool will call your existing API. Set the env vars (e.g. in the agent runtime) for base URL and optional auth.")
                            api_method = st.selectbox("HTTP method", ["GET", "POST", "PUT", "PATCH", "DELETE"], key="new_tool_method")
                            base_url_env = st.text_input("Base URL env var", value="CUSTOMER_API_URL", key="new_tool_base_env", help="Environment variable that holds the API base URL (e.g. https://api.example.com)")
                            path_template = st.text_input("Path template", value="/users/{customer_id}", key="new_tool_path", help="Use {param_name} for path parameters; the agent will pass these when calling the tool")
                            timeout = st.number_input("Timeout (seconds)", min_value=1, max_value=60, value=10, key="new_tool_timeout")
                            auth_type = st.radio("Auth", ["None", "Bearer (env var)", "API key (header + env)"], key="new_tool_auth", horizontal=True)
                            auth_header_env = None
                            api_key_header = None
                            api_key_env = None
                            if auth_type == "Bearer (env var)":
                                auth_header_env = st.text_input("Authorization header value env var", value="CUSTOMER_API_TOKEN", key="new_tool_auth_env")
                            elif auth_type == "API key (header + env)":
                                api_key_header = st.text_input("Header name", value="X-Api-Key", key="new_tool_key_header")
                                api_key_env = st.text_input("API key value env var", value="CUSTOMER_API_KEY", key="new_tool_key_env")
                            params_text = st.text_input("Parameters (comma-separated names)", value="customer_id", key="new_tool_params", help="Parameter names the agent will pass. Use same names in path template as {name}.")
    
                        if st.button("Create tool", key="create_tool_btn", type="primary"):
                            tid = (tool_id or "").strip()
                            if not tid:
                                st.error("Tool ID is required.")
                            else:
                                payload = {
                                    "tool_id": tid,
                                    "description": (description or "").strip(),
                                    "data_sources": [x.strip() for x in (data_sources or "").split(",") if x.strip()],
                                    "pii_level": pii_level,
                                    "risk_tier": risk_tier,
                                    "requires_human_approval": requires_human,
                                }
                                if template == "API-based tool (call existing API)":
                                    payload["implementation_type"] = "api"
                                    params_list = [x.strip() for x in (params_text or "").split(",") if x.strip()]
                                    path_tpl = path_template or ""
                                    parameters = []
                                    for p in params_list:
                                        param_in = "path" if ("{" + p + "}" in path_tpl) else "query"
                                        parameters.append({"name": p, "param_in": param_in, "required": True})
                                    api_cfg = {
                                        "method": api_method,
                                        "base_url_env": base_url_env,
                                        "path_template": path_tpl,
                                        "timeout_seconds": timeout,
                                        "parameters": parameters,
                                    }
                                    if auth_type == "Bearer (env var)" and auth_header_env:
                                        api_cfg["auth_header_env"] = auth_header_env
                                    if auth_type == "API key (header + env)" and api_key_header and api_key_env:
                                        api_cfg["api_key_header"] = api_key_header
                                        api_cfg["api_key_env"] = api_key_env
                                    payload["api_config"] = api_cfg
                                domains_entered = [d.strip() for d in (domain or "general").strip().split(",") if d.strip()]
                                primary_domain = domains_entered[0] if domains_entered else "general"
                                resp = requests.post(f"{API_BASE_URL}/api/v2/admin/tools/by-domain/{primary_domain}", headers=headers, json=payload, timeout=5)
                                if resp.status_code == 200:
                                    st.success(resp.json().get("message", "Tool created."))
                                    st.rerun()
                                else:
                                    st.error(resp.text or f"Error {resp.status_code}")
    
                    def tools_fallback():
                        r = requests.get(f"{API_BASE_URL}/api/v2/admin/tools", headers=headers, timeout=3)
                        if r.status_code == 200:
                            tools_dict = r.json().get("tools", {})
                            if isinstance(tools_dict, list):
                                for t in tools_dict[:30]:
                                    name = t.get("tool_id") or t.get("name", "?")
                                    with st.expander(f"{name} (v{t.get('version', '1.0.0')})"):
                                        st.json(t)
                            else:
                                for name, defn in list(tools_dict.items())[:25]:
                                    with st.expander(name):
                                        st.json(defn)
                            st.subheader("Add tool")
                            n = st.text_input("Tool name", key="tname")
                            d = st.text_input("Description", key="tdesc")
                            if st.button("Add", key="addt") and n and d:
                                rr = requests.post(f"{API_BASE_URL}/api/v2/admin/tools/{n}", headers=headers,
                                    json={"description": d, "data_sources": [], "pii_level": "low", "risk_tier": "low", "requires_human_approval": False}, timeout=3)
                                if rr.status_code == 200:
                                    st.success(f"Added {n}")
                                    st.rerun()
                                else:
                                    st.error(rr.text)
                        elif r.status_code == 403:
                            st.warning("Platform Admin required. Log in as admin@platform.com and ensure control-plane returns that role.")
                        else:
                            st.error(f"Error {r.status_code}")
    
                    # Try versioned domains first
                    r_domains = requests.get(f"{API_BASE_URL}/api/v2/admin/tools/domains", headers=headers, timeout=3)
                    if r_domains.status_code == 200:
                        domains_data = r_domains.json().get("domains", [])
                        if domains_data:
                            if st.button("🔄 Migrate flat registry to versioned", key="migrate_tools"):
                                rm = requests.post(f"{API_BASE_URL}/api/v2/admin/tools/migrate", headers=headers, timeout=5)
                                if rm.status_code == 200:
                                    st.success(rm.json().get("message", "Migrated"))
                                    st.rerun()
                                else:
                                    st.error(rm.text or "Migration failed")
                            st.caption("Tools grouped by domain. Updates create new versions and sync to repo.")
                            for dom in domains_data:
                                domain_name = dom.get("domain", "general")
                                tools_list = dom.get("tools", [])
                                with st.expander(f"**{domain_name.title()}** ({len(tools_list)} tools)", expanded=True):
                                    for t in tools_list:
                                        tid = t.get("tool_id") or t.get("name", "?")
                                        ver = t.get("version", "1.0.0")
                                        with st.container():
                                            col_a, col_b, col_c = st.columns([3, 1, 1])
                                            with col_a:
                                                st.markdown(f"**{tid}**")
                                                st.caption(t.get("description", "")[:120] + ("..." if len(t.get("description", "") or "") > 120 else ""))
                                            with col_b:
                                                st.caption(f"v{ver}")
                                            with col_c:
                                                if st.button("📊 History", key=f"history_tool_{domain_name}_{tid}"):
                                                    st.session_state[f"viewing_history_{domain_name}_{tid}"] = not st.session_state.get(f"viewing_history_{domain_name}_{tid}", False)
                                            
                                            # Version history view
                                            if st.session_state.get(f"viewing_history_{domain_name}_{tid}"):
                                                try:
                                                    rh = requests.get(f"{API_BASE_URL}/api/v2/admin/tools/by-domain/{domain_name}/{tid}/history", headers=headers, timeout=3)
                                                    if rh.status_code == 200:
                                                        history = rh.json().get("history", [])
                                                        st.info(f"**Version History for {tid}**")
                                                        for entry in history:
                                                            v = entry.get("version", "?")
                                                            prev = entry.get("previous_version", "?")
                                                            ts = entry.get("timestamp", "?")
                                                            changes = entry.get("changes", {})
                                                            with st.expander(f"v{v} (from v{prev}) - {ts}"):
                                                                if changes.get("major"):
                                                                    st.error(f"**MAJOR:** {', '.join(changes['major'])}")
                                                                if changes.get("minor"):
                                                                    st.warning(f"**MINOR:** {', '.join(changes['minor'])}")
                                                                if changes.get("patch"):
                                                                    st.info(f"**PATCH:** {', '.join(changes['patch'])}")
                                                    else:
                                                        st.warning("No version history available")
                                                except Exception as e:
                                                    st.error(f"Error loading history: {e}")
                                            
                                            if st.button("✏️ Edit", key=f"edit_tool_{domain_name}_{tid}"):
                                                st.session_state[f"editing_tool_{domain_name}_{tid}"] = True
                                            if st.session_state.get(f"editing_tool_{domain_name}_{tid}"):
                                                # Load full tool data for editing
                                                try:
                                                    r_full = requests.get(f"{API_BASE_URL}/api/v2/admin/tools/by-domain/{domain_name}/{tid}", headers=headers, timeout=3)
                                                    if r_full.status_code == 200:
                                                        tool_data = r_full.json()
                                                    else:
                                                        tool_data = t
                                                except Exception:
                                                    tool_data = t
                                                
                                                with st.form(f"form_tool_{domain_name}_{tid}"):
                                                    st.markdown(f"**Editing:** `{tid}` (current: v{tool_data.get('version', ver)})")
                                                    desc = st.text_area("Description", value=tool_data.get("description", ""), key=f"desc_{domain_name}_{tid}", height=100)
                                                    ds = st.text_input("Data sources (comma-separated)", value=",".join(tool_data.get("data_sources", [])), key=f"ds_{domain_name}_{tid}", help="e.g. PaymentProcessingSystem,TransactionEngine")
                                                    pii = st.selectbox("PII level", ["none", "low", "medium", "high"], index=["none", "low", "medium", "high"].index(tool_data.get("pii_level", "low")), key=f"pii_{domain_name}_{tid}")
                                                    risk = st.selectbox("Risk tier", ["low", "medium", "high"], index=["low", "medium", "high"].index(tool_data.get("risk_tier", "low")), key=f"risk_{domain_name}_{tid}")
                                                    human = st.checkbox("Requires human approval", value=tool_data.get("requires_human_approval", False), key=f"human_{domain_name}_{tid}")
                                                    st.caption("💡 Changes will create a new version and sync to repo files")
                                                    col_save, col_cancel = st.columns(2)
                                                    with col_save:
                                                        if st.form_submit_button("💾 Save (creates new version)", type="primary"):
                                                            payload = {"description": desc, "data_sources": [x.strip() for x in ds.split(",") if x.strip()], "pii_level": pii, "risk_tier": risk, "requires_human_approval": human}
                                                            ru = requests.put(f"{API_BASE_URL}/api/v2/admin/tools/by-domain/{domain_name}/{tid}", headers=headers, json=payload, timeout=5)
                                                            if ru.status_code == 200:
                                                                resp = ru.json()
                                                                vc = resp.get("version_change", {})
                                                                old_v = vc.get("old", "?")
                                                                new_v = vc.get("new", "?")
                                                                st.success(f"✅ Updated: v{old_v} → v{new_v} (repo synced)")
                                                                st.session_state[f"editing_tool_{domain_name}_{tid}"] = False
                                                                st.rerun()
                                                            else:
                                                                st.error(f"Error: {ru.text}")
                                                    with col_cancel:
                                                        if st.form_submit_button("❌ Cancel"):
                                                            st.session_state[f"editing_tool_{domain_name}_{tid}"] = False
                                                            st.rerun()
                                            st.divider()
                        else:
                            # No versioned domains yet – show flat list and migrate option
                            if st.button("🔄 Migrate flat registry to versioned", key="migrate_tools_flat"):
                                rm = requests.post(f"{API_BASE_URL}/api/v2/admin/tools/migrate", headers=headers, timeout=5)
                                if rm.status_code == 200:
                                    st.success(rm.json().get("message", "Migrated"))
                                    st.rerun()
                                else:
                                    st.error(rm.text or "Migration failed")
                            tools_fallback()
                    else:
                        tools_fallback()
                except Exception as e:
                    st.error(f"Request failed: {e}. Is control-plane running on {API_BASE_URL}?")
    
        with tab7:
            st.header("📜 Manage Policies")
            if not is_admin:
                st.warning("Log in as **admin@platform.com** to manage policies. Then refresh or re-run.")
            else:
                try:
                    r_domains = requests.get(f"{API_BASE_URL}/api/v2/admin/policies/domains", headers=headers, timeout=3)
                    if r_domains.status_code == 200:
                        domains_list = r_domains.json().get("domains", [])
                        if domains_list:
                            st.caption("Policies grouped by domain (domain = first path segment, e.g. payments/retry → payments).")
                            for dom in domains_list:
                                domain_name = dom.get("domain", "general")
                                policies_in_domain = dom.get("policies", [])
                                with st.expander(f"**{domain_name.title()}** ({len(policies_in_domain)} policies)", expanded=True):
                                    for p in policies_in_domain:
                                        pid = p.get("policy_id", "")
                                        with st.container():
                                            col_a, col_b = st.columns([4, 1])
                                            with col_a:
                                                st.markdown(f"**{pid}**")
                                            with col_b:
                                                if st.button("✏️ Edit", key=f"edit_policy_{pid}"):
                                                    st.session_state[f"editing_policy_{pid}"] = True
                                            
                                            if st.session_state.get(f"editing_policy_{pid}"):
                                                # Load current content for editing
                                                r2 = requests.get(f"{API_BASE_URL}/api/v2/admin/policies/{pid}", headers=headers, timeout=2)
                                                current_content = ""
                                                if r2.status_code == 200:
                                                    current_content = r2.json().get("content", "")
                                                
                                                with st.form(f"form_policy_{pid}"):
                                                    st.markdown(f"**Editing:** `{pid}`")
                                                    content = st.text_area("Rego Policy Content", value=current_content, height=300, key=f"content_{pid}")
                                                    col_save, col_cancel = st.columns(2)
                                                    with col_save:
                                                        if st.form_submit_button("💾 Save (updates repo)", type="primary"):
                                                            rr = requests.put(f"{API_BASE_URL}/api/v2/admin/policies/{pid}", headers=headers, json={"content": content}, timeout=3)
                                                            if rr.status_code == 200:
                                                                st.success(f"✅ Saved {pid} (repo updated)")
                                                                st.session_state[f"editing_policy_{pid}"] = False
                                                                st.rerun()
                                                            else:
                                                                st.error(f"Error: {rr.text}")
                                                    with col_cancel:
                                                        if st.form_submit_button("❌ Cancel"):
                                                            st.session_state[f"editing_policy_{pid}"] = False
                                                            st.rerun()
                                            else:
                                                # Show read-only view in expander
                                                with st.expander(f"View: {pid}", expanded=False):
                                                    r2 = requests.get(f"{API_BASE_URL}/api/v2/admin/policies/{pid}", headers=headers, timeout=2)
                                                    if r2.status_code == 200:
                                                        st.code(r2.json().get("content", ""), language="rego")
                                                    else:
                                                        st.error(f"Could not load policy: {r2.status_code}")
                                            st.divider()
                            st.divider()
                    r = requests.get(f"{API_BASE_URL}/api/v2/admin/policies", headers=headers, timeout=3)
                    if r.status_code == 200:
                        policies = r.json().get("policies", [])
                        if not (r_domains.status_code == 200 and r_domains.json().get("domains")):
                            for p in policies:
                                pid = p.get("policy_id", "")
                                with st.expander(pid):
                                    r2 = requests.get(f"{API_BASE_URL}/api/v2/admin/policies/{pid}", headers=headers, timeout=2)
                                    if r2.status_code == 200:
                                        st.code(r2.json().get("content", ""), language="rego")
                        st.subheader("Save policy (writes to repo)")
                        pid = st.text_input("Policy ID (e.g. payments/retry)", key="pid")
                        content = st.text_area("Rego content", key="pcontent", height=120)
                        if st.button("Save", key="savep") and pid and content:
                            rr = requests.put(f"{API_BASE_URL}/api/v2/admin/policies/{pid}", headers=headers, json={"content": content}, timeout=3)
                            if rr.status_code == 200:
                                st.success(f"Saved {pid} (repo updated)")
                                st.rerun()
                            else:
                                st.error(rr.text)
                    elif r.status_code == 403:
                        st.warning("Platform Admin required.")
                    else:
                        st.error(f"Error {r.status_code}")
                except Exception as e:
                    st.error(f"Request failed: {e}. Is control-plane running on {API_BASE_URL}?")
    
        with tab8:
            st.header("📊 Version History")
            if not st.session_state.logged_in:
                st.warning("Please log in to view version history.")
            else:
                try:
                    r_agents = requests.get(f"{API_BASE_URL}/api/v2/agent-definitions", headers=headers, timeout=3)
                    agents_list = []
                    if r_agents.status_code == 200:
                        agents_list = [a.get("agent_id") for a in r_agents.json().get("agents", []) if a.get("agent_id")]
                    if not agents_list:
                        # Fallback: try public /agents so dropdown is populated when admin list is empty or 403
                        try:
                            r_public = requests.get(f"{API_BASE_URL}/agents", headers=headers, timeout=3)
                            if r_public.status_code == 200:
                                data = r_public.json()
                                if isinstance(data, list):
                                    agents_list = [a.get("agent_id") for a in data if a.get("agent_id")]
                                else:
                                    agents_list = [a.get("agent_id") for a in data.get("agents", data.get("items", [])) if a.get("agent_id")]
                        except Exception:
                            pass
                    if r_agents.status_code == 200 or agents_list:
                        if agents_list:
                            selected_agent_history = st.selectbox("Select Agent", agents_list, key="history_agent_select")
                            if selected_agent_history:
                                try:
                                    r_history = requests.get(
                                        f"{API_BASE_URL}/api/v2/agent-definitions/{selected_agent_history}/history",
                                        headers=headers,
                                        timeout=3
                                    )
                                    if r_history.status_code == 200:
                                        history_data = r_history.json()
                                        current_version = history_data.get("current_version", "N/A")
                                        total_versions = history_data.get("total_versions", 0)
                                        
                                        st.metric("Current Version", current_version)
                                        st.metric("Total Versions", total_versions)
                                        
                                        history = history_data.get("history", [])
                                        if history:
                                            st.divider()
                                            for entry in history:
                                                version = entry.get("version", "N/A")
                                                prev_version = entry.get("previous_version", "N/A")
                                                timestamp = entry.get("timestamp", "N/A")
                                                changes = entry.get("changes", {})
                                                
                                                with st.expander(f"Version {version} (from {prev_version}) - {timestamp}"):
                                                    st.write(f"**Previous Version:** {prev_version}")
                                                    st.write(f"**Timestamp:** {timestamp}")
                                                    
                                                    if changes:
                                                        st.write("**Changes:**")
                                                        if changes.get("major"):
                                                            st.error(f"**MAJOR:** {', '.join(changes['major'])}")
                                                        if changes.get("minor"):
                                                            st.warning(f"**MINOR:** {', '.join(changes['minor'])}")
                                                        if changes.get("patch"):
                                                            st.info(f"**PATCH:** {', '.join(changes['patch'])}")
                                                    
                                                    # Fetch agent definition for this specific version to get tools and policies
                                                    try:
                                                        r_agent_version = requests.get(
                                                            f"{API_BASE_URL}/agents/{selected_agent_history}?version={version}",
                                                            headers=headers,
                                                            timeout=3
                                                        )
                                                        if r_agent_version.status_code == 200:
                                                            agent_def = r_agent_version.json()
                                                            allowed_tools = agent_def.get("allowed_tools", [])
                                                            policies = agent_def.get("policies", [])
                                                            
                                                            # Display Tools with versions
                                                            if allowed_tools:
                                                                st.divider()
                                                                st.subheader("🔧 Tools")
                                                                # Try to get tool domains first
                                                                tool_domains_map = {}
                                                                try:
                                                                    r_domains = requests.get(f"{API_BASE_URL}/api/v2/admin/tools/domains", headers=headers, timeout=2)
                                                                    if r_domains.status_code == 200:
                                                                        domains_data = r_domains.json().get("domains", [])
                                                                        for dom in domains_data:
                                                                            domain_name = dom.get("domain", "")
                                                                            tools_list = dom.get("tools", [])
                                                                            for t in tools_list:
                                                                                tool_id = t.get("tool_id") or t.get("name", "")
                                                                                if tool_id:
                                                                                    tool_domains_map[tool_id] = domain_name
                                                                except Exception:
                                                                    pass
                                                                
                                                                # Display each tool with its version
                                                                for tool_id in allowed_tools:
                                                                    tool_version = "N/A"
                                                                    tool_domain = tool_domains_map.get(tool_id, "general")
                                                                    
                                                                    # Try to get tool version from versioned storage
                                                                    try:
                                                                        r_tool = requests.get(
                                                                            f"{API_BASE_URL}/api/v2/admin/tools/by-domain/{tool_domain}/{tool_id}",
                                                                            headers=headers,
                                                                            timeout=2
                                                                        )
                                                                        if r_tool.status_code == 200:
                                                                            tool_data = r_tool.json()
                                                                            tool_version = tool_data.get("version", "1.0.0")
                                                                    except Exception:
                                                                        # Fallback: try to get from flat registry
                                                                        try:
                                                                            r_tool_flat = requests.get(f"{API_BASE_URL}/tools", timeout=2)
                                                                            if r_tool_flat.status_code == 200:
                                                                                tools_dict = r_tool_flat.json().get("tools", {})
                                                                                if isinstance(tools_dict, dict) and tool_id in tools_dict:
                                                                                    tool_version = tools_dict[tool_id].get("version", "1.0.0")
                                                                        except Exception:
                                                                            pass
                                                                    
                                                                    st.write(f"- **{tool_id}** (v{tool_version})")
                                                            else:
                                                                st.divider()
                                                                st.subheader("🔧 Tools")
                                                                st.caption("No tools configured for this version")
                                                            
                                                            # Display Policies
                                                            if policies:
                                                                st.divider()
                                                                st.subheader("📜 Policies")
                                                                for policy_id in policies:
                                                                    st.write(f"- **{policy_id}**")
                                                            else:
                                                                st.divider()
                                                                st.subheader("📜 Policies")
                                                                st.caption("No policies configured for this version")
                                                    except Exception as e:
                                                        st.caption(f"Could not load tools/policies for this version: {e}")
                                        else:
                                            st.info("No version history available. This agent hasn't been updated yet.")
                                except Exception as e:
                                    st.error(f"Error loading history: {e}")
                        else:
                            st.info("No agents found.")
                    elif r_agents.status_code == 401:
                        st.warning("Please log in to view version history.")
                    else:
                        st.error(f"Error {r_agents.status_code}: {r_agents.text}")
                except Exception as e:
                    st.warning(f"API not reachable: {e}")
    
        with tab9:
            st.header("📺 How it works")
            st.caption("Detailed flow: from user request through control-plane, regulated agents, tools, mesh, and audit.")
            # All content fits inside the dark background; scale to fit iframe
            _HOW_IT_WORKS_HTML = """
            <div class="flow-outer">
                <style>
                    * { box-sizing: border-box; }
                    .flow-outer { width: 100%; height: 100%; min-height: 480px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 14px; display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 12px; }
                    .flow-container { transform: scale(0.82); transform-origin: top center; font-family: system-ui, -apple-system, sans-serif; }
                    .vertical-section { display: flex; flex-direction: column; align-items: center; }
                    .flow-step { display: flex; flex-direction: column; align-items: center; margin: 6px 0; }
                    .edge-down { display: flex; flex-direction: column; align-items: center; margin: 4px 0; }
                    .edge-right { display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 40px; }
                    .edge-up { display: flex; flex-direction: column; align-items: center; margin: 4px 0; }
                    .arrow { color: #cbd5e1; font-size: 20px; font-weight: bold; animation: ap 1.2s ease-in-out infinite; }
                    .arrow.up { display: inline-block; }
                    .arrow.d1 { animation-delay: 0.1s; } .arrow.d2 { animation-delay: 0.25s; } .arrow.d3 { animation-delay: 0.4s; }
                    .arrow.d4 { animation-delay: 0.5s; } .arrow.d5 { animation-delay: 0.65s; } .arrow.d6 { animation-delay: 0.8s; }
                    @keyframes ap { 0%,100% { opacity: 0.4; transform: scale(1); } 50% { opacity: 1; transform: scale(1.15); } }
                    .arrow.up { animation: apUp 1.2s ease-in-out infinite; }
                    @keyframes apUp { 0%,100% { opacity: 0.4; transform: scale(1); } 50% { opacity: 1; transform: scale(1.15); } }
                    .edge-label { color: #94a3b8; font-size: 9px; margin-top: 1px; text-align: center; max-width: 88px; line-height: 1.15; }
                    .node { padding: 10px 14px; border-radius: 8px; font-weight: 700; font-size: 12px; min-width: 110px; text-align: center; box-shadow: 0 3px 12px rgba(0,0,0,0.35); }
                    .node-h { padding: 8px 10px; font-size: 11px; min-width: 64px; }
                    .node-user { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; }
                    .node-cp { background: linear-gradient(135deg, #0f3460, #16213e); color: #e2e8f0; border: 1px solid #4a5568; }
                    .node-reg { background: linear-gradient(135deg, #2d3748, #4a5568); color: #e2e8f0; }
                    .node-agent { background: linear-gradient(135deg, #11998e, #38ef7d); color: #0d0d0d; }
                    .node-policy { background: linear-gradient(135deg, #f59e0b, #d97706); color: #fff; }
                    .node-llm { background: linear-gradient(135deg, #8b5cf6, #a78bfa); color: #fff; }
                    .node-tools { background: linear-gradient(135deg, #f093fb, #f5576c); color: #fff; }
                    .node-mesh { background: linear-gradient(135deg, #4facfe, #00f2fe); color: #0d0d0d; }
                    .node-audit { background: linear-gradient(135deg, #134e4a, #0d9488); color: #e2e8f0; }
                    .node-resp { background: linear-gradient(135deg, #fa709a, #fee140); color: #0d0d0d; }
                    .node { animation: glow 5s ease-in-out infinite; }
                    .n1 { animation-delay: 0s; } .n2 { animation-delay: 0.5s; } .n3 { animation-delay: 1s; } .n4 { animation-delay: 1.5s; }
                    .n5 { animation-delay: 2s; } .n6 { animation-delay: 2.5s; } .n7 { animation-delay: 3s; } .n8 { animation-delay: 3.5s; }
                    .n9 { animation-delay: 4s; } .n10 { animation-delay: 4.5s; }
                    @keyframes glow { 0%,10%,100% { box-shadow: 0 3px 12px rgba(0,0,0,0.35); filter: brightness(1); } 5%,15%,25%,35%,45%,55%,65%,75%,85%,95% { box-shadow: 0 0 18px rgba(255,255,255,0.35); filter: brightness(1.1); } }
                    .label { color: #94a3b8; font-size: 9px; margin-top: 1px; }
                    .horizontal-section { display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 2px; margin: 6px 0; }
                    .up-section { display: flex; flex-direction: column; align-items: center; margin-top: 4px; }
                    .legend-row { display: flex; justify-content: center; gap: 10px; margin-top: 6px; padding-top: 6px; border-top: 1px solid #334155; font-size: 9px; }
                </style>
                <div class="flow-container">
                <div class="vertical-section">
                    <div class="flow-step"><div class="node node-user n1">👤 User</div><div class="label">Request</div></div>
                    <div class="edge-down"><span class="arrow">↓</span><span class="edge-label">Sends request</span></div>
                    <div class="flow-step"><div class="node node-cp n2">🖥️ Control Plane</div><div class="label">Registry · Kill-switch · RBAC</div></div>
                    <div class="edge-down"><span class="arrow d1">↓</span><span class="edge-label">Fetch definition</span></div>
                    <div class="flow-step"><div class="node node-reg n3">📋 Agent Registry</div><div class="label">YAML · version</div></div>
                    <div class="edge-down"><span class="arrow d2">↓</span><span class="edge-label">Load config</span></div>
                    <div class="flow-step"><div class="node node-agent n4">🤖 Regulated Agent</div><div class="label">Kill-switch check</div></div>
                </div>
                <div class="edge-down"><span class="arrow d3">→</span><span class="edge-label">Policy · Tools · Mesh</span></div>
                <div class="horizontal-section">
                    <div><div class="node node-policy node-h n5">📜 Policy</div><div class="label">Rego</div></div>
                    <div class="edge-right"><span class="arrow d4">→</span><span class="edge-label">Allow/deny</span></div>
                    <div><div class="node node-llm node-h n6">🧠 LLM</div><div class="label">Reasoning</div></div>
                    <div class="edge-right"><span class="arrow">→</span><span class="edge-label">Call · Invoke ⇄</span></div>
                    <div><div class="node node-tools node-h n7">🔧 Tools</div><div class="label">Gateway</div></div>
                    <div><div class="node node-mesh node-h n8">🔀 Mesh</div><div class="label">Agents</div></div>
                    <div class="edge-right"><span class="arrow d5">→</span><span class="edge-label">Log</span></div>
                    <div><div class="node node-audit node-h n9">📝 Audit</div><div class="label">CP</div></div>
                    <div class="edge-right"><span class="arrow d6">→</span><span class="edge-label">Return</span></div>
                    <div><div class="node node-resp node-h n10">💬 Response</div><div class="label">To user</div></div>
                </div>
                <div class="up-section">
                    <div class="edge-up"><span class="arrow up">↑</span><span class="edge-label">Back to user</span></div>
                    <div class="flow-step"><div class="node node-user n1">👤 User</div><div class="label">Receives response</div></div>
                </div>
                <div class="legend-row"><span class="edge-label">↓ Down</span><span class="edge-label">→ Horizontal</span><span class="edge-label">↑ Up</span><span class="edge-label">⇄ Bidirectional</span></div>
                </div>
            </div>
            """
            try:
                import streamlit.components.v1 as components
                components.html(_HOW_IT_WORKS_HTML, height=500, scrolling=False)
            except Exception:
                st.markdown("""
                **Flow:** User → **Control Plane** (Registry, Kill-switch) → **Regulated Agent** → **Policy** & **LLM** → **Tool Gateway** & **Agent Mesh** → **Audit** → **Response**.
                """)
            st.divider()
            st.markdown("""
            ### 1. User & Control Plane
            - **User** (or system) sends a request (e.g. *"Why did this payment fail?"* or *"List open incidents"*).
            - The **Control Plane** is the central platform: it hosts the **Agent Registry** (agent definitions, versions, domain/group), **Kill-switch** (disable agents or models in emergencies), and **RBAC** (who can view/use/edit which agents).
    
            ### 2. Agent definition & governance
            - **Regulated Agent** loads its **definition** from the registry (or file fallback): purpose, allowed tools, policies, model, risk tier, human-in-the-loop.
            - It checks **Kill-switch**: if the agent or its LLM model is disabled, the run is blocked.
            - **Policy** (e.g. Rego) is evaluated for the action; the control-plane policy registry returns allow/deny.
            - The agent uses an **LLM** (e.g. Gemini) for reasoning; the model can be fixed in config or set to **Auto** (platform default).
    
            ### 3. Tools & Agent Mesh
            - The agent calls **Tools** only through the **Tool Gateway**: only tools listed in its definition are allowed; calls go via the control-plane tool registry.
            - The agent can **invoke other agents** via the **Agent Mesh** (e.g. Reliability Agent calling the Healing Agent), subject to invocation policy and allowed callers.
            - **Personas & domains** (from `config/personas.yaml` and agent `domain`) control which agents a user or agent can see in the mesh.
    
            ### 4. Audit & response
            - Every tool call and important decision can be sent to the **Audit** store (control-plane) for compliance and debugging.
            - The **response** is returned to the user; for human-in-the-loop agents, high-impact actions may require explicit user approval (e.g. *approve* / *yes*) before execution.
            """)
    
st.markdown("---")
st.markdown('<p class="ravp-footer">Regulated Agent Vending Platform · <strong>RAVP v2</strong> · Manage Tools &amp; Policies<br>© 2026 Visanth Vijayan Santha. All rights reserved.</p>', unsafe_allow_html=True)
