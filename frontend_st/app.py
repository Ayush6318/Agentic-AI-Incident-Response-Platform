import pandas as pd
import requests
import streamlit as st

import api_client as api

st.set_page_config(page_title="Incident Response Agent", page_icon="🚨", layout="wide")

STEPS = {"logs": "Log analyst", "metrics": "Metrics analyst", "code": "Code analyst",
         "root_cause": "Root-cause agent", "planner": "Remediation planner"}

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
        st.error(f"{e.detail}")
    except requests.RequestException:
        st.error(f"Cannot reach the API at {api.API_URL}. Is the backend running?")
    return None


# ---------------------------------------------------------------- login
def auth_view():
    st.title("🚨 Incident Response Agent")
    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                token = run(api.login, email.strip(), password)
                if token:
                    st.session_state.token = token
                    st.session_state.user = run(api.me, token)
                    st.rerun()

    with tab_register:
        with st.form("register"):
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password (min 8 characters)", type="password", key="reg_pw")
            if st.form_submit_button("Create account"):
                if run(api.register, email.strip(), password):
                    st.success("Account created. Log in on the first tab. New accounts are viewers; "
                               "an admin must promote you to 'sre' before you can approve actions.")


# ---------------------------------------------------------------- investigation
def stream_into_ui(incident_id: int):
    done = []
    with st.status("Investigating...", expanded=True) as status:
        board = st.empty()

        def render():
            board.markdown("\n\n".join(
                f"{'✅' if k in done else '⏳'} {label}" for k, label in STEPS.items()))

        render()
        try:
            for event, data in api.stream_incident(st.session_state.token, incident_id):
                if event == "agent_done":
                    done.append(data["node"])
                    render()
                elif event == "error":
                    status.update(label="Investigation failed", state="error")
                    st.error(data["message"])
                    return
                elif event == "approval_required":
                    status.update(label="Waiting for human approval", state="complete")
                elif event == "end" and data["status"] == "done":
                    status.update(label="Investigation complete", state="complete")
        except api.ApiError as e:
            status.update(label="Could not start", state="error")
            st.error(e.detail)
        except requests.RequestException as e:
            status.update(label="Connection lost", state="error")
            st.error(f"Stream interrupted: {e}")


def approval_card(inc: dict, ctx: str):
    if st.session_state.user["role"] not in ("sre", "admin"):
        st.info("This plan needs approval from an SRE or admin.")
        return
    st.warning("**Approval required.** Approving will execute the action in the plan.")
    left, right = st.columns(2)
    for col, label, approve in ((left, "✅ Approve", True), (right, "❌ Reject", False)):
        if col.button(label, key=f"{ctx}_{'a' if approve else 'r'}_{inc['id']}", use_container_width=True):
            res = run(api.decide, st.session_state.token, inc["id"], approve)
            if res:
                st.session_state.flash = res["result"]
                st.rerun()


def show_incident(incident_id, ctx: str):
    if not incident_id:
        return
    inc = run(api.get_incident, st.session_state.token, incident_id)
    if not inc:
        return
    st.divider()
    st.subheader(f"Incident #{inc['id']}  ·  {inc['status'].replace('_', ' ')}")
    st.caption(inc["text"])
    if inc["root_cause"]:
        st.markdown("#### Root cause")
        st.markdown(inc["root_cause"])
    if inc["plan"]:
        st.markdown("#### Remediation plan")
        st.markdown(inc["plan"])
    if inc["status"] == "awaiting_approval":
        approval_card(inc, ctx)
    elif inc["status"] == "failed":
        st.warning("This investigation failed (for example a model quota error). Start a new one.")


def investigate_tab():
    text = st.text_area("Describe the incident", height=100,
                        placeholder="payment-service returns HTTP 500 after the latest deploy")
    if st.button("Investigate", type="primary", disabled=len(text.strip()) < 5):
        inc = run(api.create_incident, st.session_state.token, text.strip())
        if inc:
            st.session_state.incident_id = inc["id"]
            stream_into_ui(inc["id"])
    show_incident(st.session_state.incident_id, "inv")


def history_tab():
    rows = run(api.list_incidents, st.session_state.token)
    if not rows:
        st.info("No incidents yet.")
        return
    df = pd.DataFrame(rows)[["id", "text", "status", "created"]]
    st.dataframe(df, hide_index=True, use_container_width=True)
    chosen = st.selectbox("Open an incident", [r["id"] for r in rows], format_func=lambda i: f"#{i}")
    show_incident(chosen, "hist")


def main_view():
    user = st.session_state.user
    st.sidebar.markdown(f"**{user['email']}**")
    st.sidebar.caption(f"Role: {user['role']}")
    if st.sidebar.button("Log out"):
        logout()
        st.rerun()

    if msg := st.session_state.pop("flash", None):
        st.toast(msg, icon="✅")

    st.title("🚨 Incident Response Agent")
    tab_new, tab_history = st.tabs(["Investigate", "History"])
    with tab_new:
        investigate_tab()
    with tab_history:
        history_tab()


if st.session_state.token and st.session_state.user:
    main_view()
else:
    auth_view()