import streamlit as st
import time
from google import genai
from google.genai import types
from google.genai import errors

# Page setup
st.set_page_config(page_title="AI Debate Arena", page_icon="⚖️", layout="wide")
st.title("⚖️ Gemini Multi-Agent Debate Arena")
st.caption("Two distinct Gemini agents debate a topic from isolated perspectives before a Judge issues the final verdict.")

# Setup Gemini Client safely
api_key = st.secrets["GEMINI_API_KEY"].strip()
client = genai.Client(api_key=api_key)

# High-volume, active Flash-Lite and Flash models to cycle through
MODELS_TO_TRY = [
    "gemini-3.8-flash"
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
            time.sleep(1.5)  # Breather between requests
            return response.text

        except errors.ClientError as e:
            # Catches 429 Quota Exceeded or 404 Model Not Found
            last_error = e
            if "429" in str(e) or "404" in str(e):
                st.toast(f"Switching from {model_name} due to quota/availability...", icon="🔄")
                continue
            raise e

        except errors.ServerError as e:
            # Catches 503 Server Busy / Capacity Spikes
            last_error = e
            if "503" in str(e):
                st.toast(f"{model_name} is busy. Trying fallback model...", icon="⏳")
                time.sleep(2)
                continue
            raise e

    # If all models in the list fail, raise the last recorded error
    raise last_error

# User input
question = st.text_input(
    "Enter a topic or decision to debate:",
    placeholder="e.g., Should I specialize deeply in one skill or become a broad generalist?"
)

if st.button("Start Debate", type="primary"):
    if not question.strip():
        st.warning("Please enter a question or topic first!")
    else:
        # --- ROUND 1: Independent Arguments ---
        st.subheader("🥊 Round 1: Independent Arguments")
        col1, col2 = st.columns(2)

        with col1:
            with st.spinner("Debater A (Specialist) is formulating an argument..."):
                agent_a = ask_agent(
                    "You are Debater A: A rigorous advocate for deep specialization, elite mastery, and uncompromising standards.",
                    question
                )
            st.info("### 🤓 Debater A (Specialist)")
            st.write(agent_a)

        with col2:
            with st.spinner("Debater B (Generalist) is formulating an argument..."):
                agent_b = ask_agent(
                    "You are Debater B: A pragmatist advocating adaptability, cross-domain thinking, speed, and versatility.",
                    question
                )
            st.success("### 🌐 Debater B (Generalist)")
            st.write(agent_b)

        st.divider()

        # --- ROUND 2: The Rebuttals ---
        st.subheader("🔥 Round 2: The Rebuttals")
        col3, col4 = st.columns(2)

        with col3:
            with st.spinner("Debater A is critiquing Debater B..."):
                rebuttal_a = ask_agent(
                    "You are Debater A. Directly critique the opposing argument. Point out its weak assumptions and fatal flaws.",
                    f"Topic: {question}\n\nDebater B argued:\n{agent_b}"
                )
            st.info("### ⚔️ Debater A's Attack")
            st.write(rebuttal_a)

        with col4:
            with st.spinner("Debater B is critiquing Debater A..."):
                rebuttal_b = ask_agent(
                    "You are Debater B. Directly critique the opposing argument. Point out its weak assumptions and fatal flaws.",
                    f"Topic: {question}\n\nDebater A argued:\n{agent_a}"
                )
            st.success("### ⚔️ Debater B's Attack")
            st.write(rebuttal_b)

        st.divider()

        # --- ROUND 3: The Judge's Verdict ---
        st.subheader("🏆 Final Decision: The Arbiter")
        with st.spinner("The Judge is synthesizing the debate..."):
            judge_prompt = f"""
            Topic: {question}

            Debater A:
            {agent_a}
            Rebuttal:
            {rebuttal_a}

            Debater B:
            {agent_b}
            Rebuttal:
            {rebuttal_b}

            Task: Identify the strongest factual points, discard rhetorical fluff, and declare a comprehensive, balanced verdict.
            """
            verdict = ask_agent(
                "You are an impartial, razor-sharp judge evaluating a formal debate. Be objective and deliver a clear synthesis.",
                judge_prompt
            )

        st.markdown(verdict)
