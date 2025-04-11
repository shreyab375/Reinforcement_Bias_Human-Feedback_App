import streamlit as st
import pandas as pd
import io

# Set page to wide layout
st.set_page_config(layout="wide")

# Basic initialization of session state
if 'init' not in st.session_state:
    st.session_state.init = True
    st.session_state.scores_dict = {}  # New name to avoid conflicts
    st.session_state.current_idx = 0   # New name to avoid conflicts
    st.session_state.saved_qs = set()  # New name to avoid conflicts
    st.session_state.all_scores = []   # Keep a running list of all scores for download

# Load data function with error handling
@st.cache_data
def load_data():
    try:
        return pd.read_csv("llm_rag_drift_log_20250410_214712.csv")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Load data
df = load_data()

# Basic validation
if df.empty:
    st.warning("No data available. Please check your CSV file.")
    st.stop()

if "question_id" not in df.columns:
    st.error("CSV file must contain a 'question_id' column")
    st.stop()

# Process data
df["question_id"] = df["question_id"].astype(str)
grouped = df.groupby("question_id")
question_ids = list(grouped.groups.keys())

if not question_ids:
    st.warning("No questions found in data.")
    st.stop()

# Title
st.title("LLM Response Scoring App")

# Download section in sidebar
with st.sidebar:
    st.header("Download Scores")
    
    # Convert the stored scores to a DataFrame
    if st.session_state.all_scores:
        scores_df = pd.DataFrame(st.session_state.all_scores)
        
        # CSV download option
        csv_data = scores_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download as CSV",
            data=csv_data,
            file_name="llm_scoring_results.csv",
            mime="text/csv"
        )
    else:
        st.info("Score some responses to enable downloads")

# Make sure index is valid
if st.session_state.current_idx >= len(question_ids):
    st.session_state.current_idx = 0

# Get current question
current_q_id = question_ids[st.session_state.current_idx]
group = grouped.get_group(current_q_id)

# Progress display
st.progress(st.session_state.current_idx / len(question_ids))
st.write(f"Question {st.session_state.current_idx + 1} of {len(question_ids)}")

# Display question
st.header(f"Question ID: {current_q_id}")
st.subheader(f"Question: {group.iloc[0]['question_text']}")
st.write("---")

# Create columns for responses
num_responses = len(group)
cols = st.columns(num_responses)

# Process responses
for i, (_, row) in enumerate(group.iterrows()):
    model_name = row['llm']
    resp_key = f"response_{current_q_id}_{model_name}"
    score_key = f"score_{current_q_id}_{model_name}"
    
    with cols[i]:
        #st.markdown(f"### {model_name}")
        st.text_area("Response", value=row["response"], height=900, key=resp_key)
        
        # Rating widget
        if score_key not in st.session_state:
            st.session_state[score_key] = 3  # Default score
            
        score = st.select_slider(
            "Rate response (1=Poor, 5=Excellent)",
            options=[1, 2, 3, 4, 5],
            value=st.session_state[score_key],
            key=f"slider_{score_key}"
        )
        
        # Store score in separate session state variable
        st.session_state[score_key] = score
        
        # Also store in our dictionary for saving later
        if current_q_id not in st.session_state.scores_dict:
            st.session_state.scores_dict[current_q_id] = {}
            
        st.session_state.scores_dict[current_q_id][model_name] = {
            "question_id": current_q_id,
            "llm": model_name,
            "score": score
        }

st.write("---")

# Navigation and save buttons
col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.current_idx > 0:
        if st.button("⬅️ Previous Question"):
            st.session_state.current_idx -= 1
            st.rerun()

with col2:
    save_label = "Save Scores" if current_q_id not in st.session_state.saved_qs else "Update Scores"
    if st.button(f"💾 {save_label}"):
        # Get scores for current question
        scores_to_save = []
        if current_q_id in st.session_state.scores_dict:
            for model, data in st.session_state.scores_dict[current_q_id].items():
                scores_to_save.append(data)
                # Add to all_scores list if not already saved
                if current_q_id not in st.session_state.saved_qs:
                    st.session_state.all_scores.append(data)
                # If already saved, update the existing entry
                else:
                    # Find and update the existing entry
                    for i, item in enumerate(st.session_state.all_scores):
                        if item["question_id"] == current_q_id and item["llm"] == model:
                            st.session_state.all_scores[i] = data
                            break
        
        if scores_to_save:
            # Mark as saved
            st.session_state.saved_qs.add(current_q_id)
            st.success(f"Scores saved for question {current_q_id}!")
            
            # Move to next question
            if st.session_state.current_idx < len(question_ids) - 1:
                st.session_state.current_idx += 1
                st.rerun()
            else:
                st.success("All questions have been scored!")
        else:
            st.error("No scores to save.")

with col3:
    if st.session_state.current_idx < len(question_ids) - 1:
        if st.button("➡️ Next Question"):
            st.session_state.current_idx += 1
            st.rerun()

# Save all button
if st.button("💾 Save All Remaining Scores"):
    # Collect all unsaved scores
    newly_saved = 0
    for qid in st.session_state.scores_dict:
        if qid not in st.session_state.saved_qs:
            for model, data in st.session_state.scores_dict[qid].items():
                st.session_state.all_scores.append(data)
                newly_saved += 1
            st.session_state.saved_qs.add(qid)
    
    if newly_saved > 0:
        st.success(f"Saved {newly_saved} scores!")
    else:
        st.info("No unsaved scores to save.")