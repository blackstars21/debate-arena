import streamlit as st
import time
from google import genai
from google.genai import types
from google.genai import errors

# Page setup
st.set_page_config(page_title="AI Debate Arena", page_icon="⚖️", layout="wide")

# Setup Gemini Client
api_key = st.secrets["GEMINI_API_KEY"].strip()
client = genai.Client(api_key=api_key)

MODELS_TO_TRY = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-pro-preview"
]

def ask_agent(role: str, prompt: str) -> str:
    last_error = None
    for model_name in MODELS_TO_TRY:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=role,
                    temperature=0.7
                )
            )
            time.sleep(1.5)
            return response.text
        except errors.ClientError as e:
            last_error = e
            if "429" in str(e) or "404" in str(e):
                continue
            raise e
        except errors.ServerError as e:
            last_error = e
            if "503" in str(e):
                time.sleep(2)
                continue
            raise e
    raise last_error

# --- SESSION HISTORY INITIALIZATION ---
if "history" not in st.session_state:
    st.session_state.history = []

if "active_debate_idx" not in st.session_state:
    st.session_state.active_debate_idx = None

# --- SIDEBAR HISTORY ---
with st.sidebar:
    st.title("🗂️ Debate History")
    if st.button("➕ New Debate", use_container_width=True):
        st.session_state.active_debate_idx = None
        st.rerun()

    st.divider()

    if st.session_state.history:
        for idx, item in enumerate(reversed(st.session_state.history)):
            real_idx = len(st.session_state.history) - 1 - idx
            label = item["question"]
            short_label = label[:24] + "..." if len(label) > 24 else label
            icon = "⚡" if item.get("mode") == "Executive Summary" else "💬"
            if st.button(f"{icon} {short_label}", key=f"hist_{real_idx}", use_container_width=True):
                st.session_state.active_debate_idx = real_idx
                st.rerun()
    else:
        st.caption("No debates recorded yet.")

# --- MAIN SCREEN ---
st.title("⚖️ Gemini Multi-Agent Debate Arena")

# Function to render a debate record
def render_debate(data):
    st.info(f"**Topic:** {data['question']}")

    if data.get("mode") == "Executive Summary":
        st.subheader("⚡ Executive Summary & Verdict")
        st.markdown(data["verdict"])

        with st.expander("🔍 View Raw Agent Transcripts"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🤓 Specialist Pitch & Rebuttal")
                st.write(data["agent_a"])
                st.divider()
                st.write(data["rebuttal_a"])
            with c2:
                st.markdown("#### 🌐 Generalist Pitch & Rebuttal")
                st.write(data["agent_b"])
                st.divider()
                st.write(data["rebuttal_b"])
    else:
        st.subheader("🥊 Round 1: Arguments")
        c1, c2 = st.columns(2)
        with c1:
            st.info("### 🤓 Debater A (Specialist)")
            st.write(data["agent_a"])
        with c2:
            st.success("### 🌐 Debater B (Generalist)")
            st.write(data["agent_b"])

        st.divider()
        st.subheader("🔥 Round 2: Rebuttals")
        c3, c4 = st.columns(2)
        with c3:
            st.info("### ⚔️ Debater A's Attack")
            st.write(data["rebuttal_a"])
        with c4:
            st.success("### ⚔️ Debater B's Attack")
            st.write(data["rebuttal_b"])

        st.divider()
        st.subheader("🏆 Arbiter Verdict")
        st.markdown(data["verdict"])

# View selected historical debate
if st.session_state.active_debate_idx is not None:
    saved = st.session_state.history[st.session_state.active_debate_idx]
    render_debate(saved)

# Otherwise, create a new debate
else:
    question = st.text_input(
        "Enter a topic or decision to debate:",
        placeholder="e.g., Should I specialize deeply in one skill or become a broad generalist?"
    )

    mode = st.radio(
        "Choose Output Format:",
        options=["Full Arena Debate (Round-by-Round)", "Executive Summary (Quick Verdict & Stance Breakdown)"],
        horizontal=True
    )

    if st.button("Start Debate", type="primary"):
        if not question.strip():
            st.warning("Please enter a question or topic first!")
        else:
            with st.spinner("Round 1: Generating independent arguments..."):
                agent_a = ask_agent(
                    "You are Debater A: A rigorous advocate for deep specialization, elite mastery, and uncompromising standards.",
                    question
                )
                agent_b = ask_agent(
                    "You are Debater B: A pragmatist advocating adaptability, cross-domain thinking, speed, and versatility.",
                    question
                )

            with st.spinner("Round 2: Cross-examining arguments..."):
                rebuttal_a = ask_agent(
                    "You are Debater A. Directly critique the opposing argument. Point out its weak assumptions and fatal flaws.",
                    f"Topic: {question}\n\nDebater B argued:\n{agent_b}"
                )
                rebuttal_b = ask_agent(
                    "You are Debater B. Directly critique the opposing argument. Point out its weak assumptions and fatal flaws.",
                    f"Topic: {question}\n\nDebater A argued:\n{agent_a}"
                )

            with st.spinner("Round 3: Synthesizing verdict..."):
                if "Executive Summary" in mode:
                    judge_prompt = f"""
                    Topic: {question}

                    Debater A (Specialist):
                    {agent_a}
                    Rebuttal: {rebuttal_a}

                    Debater B (Generalist):
                    {agent_b}
                    Rebuttal: {rebuttal_b}

                    Task:
                    Provide an executive summary structured strictly as:
                    1. **Agent A's Core Stance**: 2-3 bullet points summarizing their strongest arguments.
                    2. **Agent B's Core Stance**: 2-3 bullet points summarizing their strongest arguments.
                    3. **The Clash**: 1 short paragraph identifying the fundamental trade-off.
                    4. **Final Verdict**: Your definitive recommendation and practical conclusion.
                    """
                else:
                    judge_prompt = f"""
                    Topic: {question}

                    Debater A: {agent_a}
                    Rebuttal: {rebuttal_a}

                    Debater B: {agent_b}
                    Rebuttal: {rebuttal_b}

                    Task: Formally evaluate the debate, discard rhetorical fluff, highlight valid evidence, and deliver an impartial verdict.
                    """

                verdict = ask_agent(
                    "You are an impartial, razor-sharp judge evaluating a formal debate.",
                    judge_prompt
                )

            chosen_mode = "Executive Summary" if "Executive Summary" in mode else "Full Debate"
            record = {
                "question": question,
                "mode": chosen_mode,
                "agent_a": agent_a,
                "agent_b": agent_b,
                "rebuttal_a": rebuttal_a,
                "rebuttal_b": rebuttal_b,
                "verdict": verdict
            }
            st.session_state.history.append(record)
            st.session_state.active_debate_idx = len(st.session_state.history) - 1
            st.rerun()
