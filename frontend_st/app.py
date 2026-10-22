import html

import pandas as pd
import requests
import streamlit as st

import api_client as api

# ---------------------------------------------------------------- icons
# Material Symbols (outline) are built into Streamlit >= 1.40, so no extra
# dependency is needed. On older versions icons are silently omitted.
def _icons_supported() -> bool:
    try:
        major, minor = (int(p) for p in st.__version__.split(".")[:2])
        return (major, minor) >= (1, 40)
    except Exception:
        return False


ICONS_OK = _icons_supported()


def ic(name: str):
    return f":material/{name}:" if ICONS_OK else None


# ---------------------------------------------------------------- config & state
st.set_page_config(
    page_title="Guardian AI - Incident Response",
    page_icon=ic("shield") if ICONS_OK else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- design tokens
TOKENS = {
    "bg": "#F7F8FA",
    "surface": "#FFFFFF",
    "surface_alt": "#F1F3F6",
    "text": "#171A23",
    "muted": "#687182",
    "border": "#E3E7ED",
    "accent": "#4F46E5",
    "accent_hover": "#4338CA",
    "accent_soft": "#EEF0FF",
}

# semantic status -> (label, text color, background, border)
STATUS_STYLES = {
    "awaiting_approval": ("Awaiting approval", "#92400E", "#FEF3C7", "#FDE68A"),
    "done": ("Resolved", "#166534", "#DCFCE7", "#BBF7D0"),
    "failed": ("Failed", "#991B1B", "#FEE2E2", "#FECACA"),
    "investigating": ("Investigating", "#3730A3", "#EEF0FF", "#C7D2FE"),
}
NEUTRAL_STYLE = ("#475569", "#F1F5F9", "#E2E8F0")

STEPS = {
    "logs": "Log Analysis",
    "metrics": "Metrics Correlation",
    "code": "Codebase Scanning",
    "root_cause": "Root Cause Inference",
    "planner": "Remediation Planning",
}

MIN_INCIDENT_CHARS = 10

CSS = f"""
<style>
    :root {{
        --g-bg: {TOKENS['bg']};
        --g-surface: {TOKENS['surface']};
        --g-alt: {TOKENS['surface_alt']};
        --g-text: {TOKENS['text']};
        --g-muted: {TOKENS['muted']};
        --g-border: {TOKENS['border']};
        --g-accent: {TOKENS['accent']};
        --g-accent-hover: {TOKENS['accent_hover']};
        --g-accent-soft: {TOKENS['accent_soft']};
        --g-radius: 8px;
    }}

    /* Layout: centered container with a sensible max width */
    .block-container {{
        max-width: 1120px;
        padding-top: 2.25rem;
        padding-bottom: 3rem;
    }}
    header[data-testid="stHeader"] {{ background: transparent; }}
    #MainMenu, footer {{ visibility: hidden; }}

    /* Typography */
    h1, h2, h3, h4 {{ letter-spacing: -0.01em; color: var(--g-text); }}
    h3 {{ font-size: 1.05rem; font-weight: 600; }}

    /* Page header */
    .g-page-title {{
        font-size: 1.5rem; font-weight: 600; line-height: 1.3;
        margin: 0; color: var(--g-text);
    }}
    .g-page-desc {{
        font-size: 0.9rem; color: var(--g-muted); margin: 0.25rem 0 1.25rem 0;
        max-width: 720px;
    }}
    .g-section {{
        font-size: 0.78rem; font-weight: 600; color: var(--g-muted);
        letter-spacing: 0.02em; margin: 1.5rem 0 0.5rem 0;
    }}

    /* Sidebar brand + account */
    .g-brand {{ font-size: 1.05rem; font-weight: 600; color: var(--g-text); line-height: 1.2; }}
    .g-brand-sub {{ font-size: 0.78rem; color: var(--g-muted); margin-top: 2px; }}
    .g-account-email {{
        font-size: 0.85rem; color: var(--g-text); word-break: break-all;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    .g-account-label {{ font-size: 0.72rem; color: var(--g-muted); margin-bottom: 2px; }}

    /* Badges */
    .g-badge {{
        display: inline-block; padding: 2px 9px; border-radius: 999px;
        font-size: 0.75rem; font-weight: 500; line-height: 1.5;
        border: 1px solid transparent; white-space: nowrap;
    }}

    /* Agent step list */
    .g-step {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 6px 0; border-bottom: 1px solid var(--g-border); font-size: 0.88rem;
    }}
    .g-step:last-child {{ border-bottom: none; }}
    .g-step-name {{ color: var(--g-text); }}

    /* Tabs: understated, accent underline */
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--g-border); }}
    .stTabs [data-baseweb="tab"] {{
        height: 42px; padding: 0 14px; color: var(--g-muted); font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{ color: var(--g-accent); }}
    .stTabs [data-baseweb="tab-highlight"] {{ background-color: var(--g-accent); }}

    /* Buttons */
    .stButton > button, .stFormSubmitButton > button {{
        border-radius: 6px; height: 2.4rem; font-weight: 500;
        transition: background-color .12s ease, border-color .12s ease;
    }}

    /* Bordered containers and dataframes */
    [data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: var(--g-radius); }}
    [data-testid="stDataFrame"] {{
        border: 1px solid var(--g-border); border-radius: var(--g-radius); overflow: hidden;
    }}

    /* Metrics */
    [data-testid="stMetricLabel"] {{ color: var(--g-muted); }}
    [data-testid="stMetricValue"] {{ font-size: 1.6rem; font-weight: 600; }}

    /* Incident body text */
    .g-incident-text {{
        background: var(--g-alt); border: 1px solid var(--g-border);
        border-radius: var(--g-radius); padding: 12px 14px; font-size: 0.9rem;
        white-space: pre-wrap; word-break: break-word;
    }}

    /* Auth */
    .g-auth-title {{ font-size: 1.4rem; font-weight: 600; text-align: center; margin: 3rem 0 .25rem 0; }}
    .g-auth-desc {{ text-align: center; color: var(--g-muted); font-size: .9rem; margin-bottom: 1.5rem; }}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- ui helpers
def badge(status: str) -> str:
    if status in STATUS_STYLES:
        label, fg, bg, border = STATUS_STYLES[status]
    else:
        label = str(status).replace("_", " ").capitalize()
        fg, bg, border = NEUTRAL_STYLE
    return (
        f"<span class='g-badge' style='color:{fg};background:{bg};border-color:{border};'>"
        f"{html.escape(label)}</span>"
    )


def status_label(status: str) -> str:
    if status in STATUS_STYLES:
        return STATUS_STYLES[status][0]
    return str(status).replace("_", " ").capitalize()


def page_header(title: str, description: str = ""):
    st.markdown(f"<p class='g-page-title'>{html.escape(title)}</p>", unsafe_allow_html=True)
    if description:
        st.markdown(f"<p class='g-page-desc'>{html.escape(description)}</p>", unsafe_allow_html=True)


def section(label: str):
    st.markdown(f"<div class='g-section'>{html.escape(label.upper())}</div>", unsafe_allow_html=True)


for key in ("token", "user", "incident_id"):
    st.session_state.setdefault(key, None)


def logout():
    for key in ("token", "user", "incident_id"):
        st.session_state[key] = None


def run(fn, *args):
    """Call the API. On failure show a friendly message and return None."""
    try:
        return fn(*args)
    except api.ApiError as e:
        if e.status == 401:
            logout()
            st.rerun()
        st.error(f"{e.detail}", icon=ic("error"))
    except requests.RequestException:
        st.error(
            f"Cannot reach the API at {api.API_URL}. Is the backend running?",
            icon=ic("cloud_off"),
        )
    return None


# ---------------------------------------------------------------- login
def auth_view():
    st.markdown("<div class='g-auth-title'>Guardian AI</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='g-auth-desc'>Sign in to access the incident response workspace.</div>",
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        with st.container(border=True):
            tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

            with tab_login:
                with st.form("login", clear_on_submit=True):
                    email = st.text_input("Work email", placeholder="name@company.com")
                    password = st.text_input("Password", type="password")
                    submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                    if submit:
                        if not email.strip() or not password:
                            st.error("Enter your email and password.", icon=ic("error"))
                        else:
                            token = run(api.login, email.strip(), password)
                            if token:
                                st.session_state.token = token
                                st.session_state.user = run(api.me, token)
                                st.rerun()

            with tab_register:
                with st.form("register", clear_on_submit=True):
                    email = st.text_input("Work email", key="reg_email", placeholder="name@company.com")
                    password = st.text_input(
                        "Password", type="password", key="reg_pw", help="Minimum 8 characters required."
                    )
                    submit = st.form_submit_button("Create Account", use_container_width=True)

                    if submit:
                        if not email.strip() or not password:
                            st.error("Enter an email and a password.", icon=ic("error"))
                        elif run(api.register, email.strip(), password):
                            st.success("Account created. Please sign in.", icon=ic("check_circle"))
                            st.caption(
                                "New accounts default to viewer access. An administrator must "
                                "promote you to 'sre' for execution privileges."
                            )


# ---------------------------------------------------------------- investigation
def _render_steps(board, done: list):
    rows = []
    for key, label in STEPS.items():
        if key in done:
            state = "<span class='g-badge' style='color:#166534;background:#DCFCE7;border-color:#BBF7D0;'>Completed</span>"
        else:
            fg, bg, border = NEUTRAL_STYLE
            state = f"<span class='g-badge' style='color:{fg};background:{bg};border-color:{border};'>Pending</span>"
        rows.append(f"<div class='g-step'><span class='g-step-name'>{html.escape(label)}</span>{state}</div>")
    board.markdown("".join(rows), unsafe_allow_html=True)


def stream_into_ui(incident_id: int):
    done = []
    with st.status("Investigation in progress", expanded=True) as status:
        board = st.empty()
        _render_steps(board, done)
        try:
            for event, data in api.stream_incident(st.session_state.token, incident_id):
                if event == "agent_done":
                    done.append(data["node"])
                    _render_steps(board, done)
                elif event == "error":
                    status.update(label="Investigation halted due to an error", state="error")
                    st.error(data["message"], icon=ic("error"))
                    return
                elif event == "approval_required":
                    status.update(label="Awaiting human approval", state="complete")
                elif event == "end" and data["status"] == "done":
                    status.update(label="Investigation complete", state="complete")
        except api.ApiError as e:
            status.update(label="Could not start investigation", state="error")
            st.error(e.detail, icon=ic("error"))
        except requests.RequestException as e:
            status.update(label="Stream interrupted", state="error")
            st.error(f"Stream interrupted: {e}", icon=ic("cloud_off"))


def approval_card(inc: dict, ctx: str):
    if st.session_state.user["role"] not in ("sre", "admin"):
        st.info(
            "Execution is locked. This remediation plan requires approval from an SRE or administrator.",
            icon=ic("lock"),
        )
        return

    st.warning(
        "Action required. Approving will execute the remediation script in the production environment.",
        icon=ic("warning"),
    )

    c1, c2, _ = st.columns([1.2, 1, 1.8])
    if c1.button(
        "Approve and Execute", key=f"{ctx}_a_{inc['id']}", type="primary",
        use_container_width=True, icon=ic("check"),
    ):
        res = run(api.decide, st.session_state.token, inc["id"], True)
        if res:
            st.session_state.flash = res["result"]
            st.rerun()

    if c2.button(
        "Reject Plan", key=f"{ctx}_r_{inc['id']}", use_container_width=True, icon=ic("close"),
    ):
        res = run(api.decide, st.session_state.token, inc["id"], False)
        if res:
            st.session_state.flash = res["result"]
            st.rerun()


def show_incident(incident_id, ctx: str):
    if not incident_id:
        return

    inc = run(api.get_incident, st.session_state.token, incident_id)
    if not inc:
        return

    st.write("")
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"### Incident #{inc['id']}")
        with c2:
            st.markdown(
                f"<div style='text-align:right;padding-top:.5rem;'>{badge(inc['status'])}</div>",
                unsafe_allow_html=True,
            )

        section("Reported context")
        st.markdown(
            f"<div class='g-incident-text'>{html.escape(inc['text'])}</div>", unsafe_allow_html=True
        )

        if inc["root_cause"]:
            section("Analysis")
            with st.expander("Root cause analysis", expanded=True):
                st.markdown(inc["root_cause"])

        if inc["plan"]:
            with st.expander("Proposed remediation plan", expanded=True):
                st.markdown(inc["plan"])

        if inc["status"] == "awaiting_approval":
            st.write("")
            approval_card(inc, ctx)
        elif inc["status"] == "failed":
            st.error(
                "This investigation failed (for example, a model context limit or quota). "
                "Start a new investigation.",
                icon=ic("error"),
            )


def investigate_tab():
    page_header(
        "Incident Workspace",
        "Describe an observed anomaly. The agents analyze logs, metrics and code to infer a root "
        "cause and propose a remediation plan.",
    )

    with st.container(border=True):
        text = st.text_area(
            "Incident description",
            key="incident_text",
            height=130,
            placeholder="Example: checkout-service is returning HTTP 500s and p95 latency rose to 4s "
            "starting around 10:00 UTC after the latest deploy.",
            help=f"Minimum {MIN_INCIDENT_CHARS} characters.",
        )

        c1, c2 = st.columns([1.2, 3])
        with c1:
            submitted = st.button(
                "Start Investigation", type="primary", use_container_width=True, icon=ic("play_arrow"),
            )
        with c2:
            st.caption("Include the affected service, symptoms and when they started for better results.")

        if submitted:
            if len(text.strip()) < MIN_INCIDENT_CHARS:
                st.error(
                    f"Describe the incident in at least {MIN_INCIDENT_CHARS} characters.",
                    icon=ic("error"),
                )
            else:
                with st.spinner("Creating incident..."):
                    inc = run(api.create_incident, st.session_state.token, text.strip())
                if inc:
                    st.session_state.incident_id = inc["id"]
                    stream_into_ui(inc["id"])

    show_incident(st.session_state.incident_id, "inv")


def history_tab():
    page_header("Incident History", "Previous investigations and their current state.")

    rows = run(api.list_incidents, st.session_state.token)
    if not rows:
        st.info("No incidents have been recorded in this workspace yet.", icon=ic("inbox"))
        return

    df = pd.DataFrame(rows)[["id", "status", "text", "created"]]

    with st.container(border=True):
        m1, m2, m3 = st.columns(3)
        m1.metric("Total investigations", len(df))
        m2.metric("Awaiting approval", int((df["status"] == "awaiting_approval").sum()))
        m3.metric("Resolved", int((df["status"] == "done").sum()))

    section("Incidents")
    view = df.copy()
    view["status"] = view["status"].map(status_label)
    st.dataframe(
        view,
        hide_index=True,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", format="#%d", width="small"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "text": st.column_config.TextColumn("Description", width="large"),
            "created": st.column_config.DatetimeColumn("Created", format="MMM DD, YYYY - HH:mm"),
        },
    )

    section("Details")
    c1, _ = st.columns([2, 3])
    with c1:
        chosen = st.selectbox(
            "Select an incident",
            [r["id"] for r in rows],
            format_func=lambda i: f"Incident #{i}",
        )
    show_incident(chosen, "hist")


def sidebar():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(
            f"<div class='g-brand'>Guardian AI</div><div class='g-brand-sub'>Incident Response</div>",
            unsafe_allow_html=True,
        )
        st.write("")
        st.divider()
        st.markdown("<div class='g-account-label'>Signed in as</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='g-account-email'>{html.escape(str(user['email']))}</div>",
            unsafe_allow_html=True,
        )
        role = str(user["role"])
        fg, bg, border = ("#166534", "#DCFCE7", "#BBF7D0") if role in ("sre", "admin") else NEUTRAL_STYLE
        st.markdown(
            f"<div style='margin:8px 0 14px 0;'><span class='g-badge' "
            f"style='color:{fg};background:{bg};border-color:{border};'>"
            f"{html.escape(role.capitalize())}</span></div>",
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", use_container_width=True, icon=ic("logout")):
            logout()
            st.rerun()


def main_view():
    sidebar()

    if msg := st.session_state.pop("flash", None):
        st.toast(msg, icon=ic("check_circle"))

    tab_new, tab_history = st.tabs(["Active Investigation", "Incident History"])
    with tab_new:
        investigate_tab()
    with tab_history:
        history_tab()


inject_css()

if st.session_state.token and st.session_state.user:
    main_view()
else:
    auth_view()
