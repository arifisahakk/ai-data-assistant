import streamlit as st
import pandas as pd
import json
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

# 1. Load Environment Variables (API Keys)
load_dotenv()

# 2. Configure the Streamlit Page
st.set_page_config(page_title="Dataset AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 Application Data AI Assistant")
st.markdown("Ask natural language questions about your `public_applications_2.json` dataset.")

# 3. Data Ingestion & Normalization
# We use st.cache_data so the system doesn't re-process the JSON on every chat interaction
@st.cache_data
def load_and_prepare_data(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    records = data.get('records', [])
    rows = []
    
    for record in records:
        # SAFETY CHECK 1: Ensure 'record' is actually a dictionary
        if not isinstance(record, dict):
            continue
            
        app_info = record.get('application', {})
        
        # SAFETY CHECK 2: Ensure 'app_info' is a dictionary and isn't empty
        if not isinstance(app_info, dict) or not app_info:
            continue
            
        # Clean up application-level data (Company and Purpose only)
        company = str(app_info.get('company', '')).strip() if app_info.get('company') else None
        purpose = str(app_info.get('purpose', '')).strip() if app_info.get('purpose') else None
        
        # --- Extract Application-Level Start Date & Entering Time ---
        app_syncd = app_info.get('syncd')
        start_date = None
        entering_time = None
        if app_syncd and isinstance(app_syncd, str) and ' ' in app_syncd:
            parts = app_syncd.split(' ')
            start_date = parts[0]     # Grabs the "YYYY-MM-DD"
            if len(parts) > 1:
                entering_time = parts[1]  # Grabs the "HH:MM:SS"
                
        # --- Extract Application-Level End Date & Leaving Time ---
        app_synmd = app_info.get('synmd')
        end_date = None
        leaving_time = None
        if app_synmd and isinstance(app_synmd, str) and ' ' in app_synmd:
            parts = app_synmd.split(' ')
            end_date = parts[0]       # Grabs the "YYYY-MM-DD"
            if len(parts) > 1:
                leaving_time = parts[1]   # Grabs the "HH:MM:SS"

        # SAFETY CHECK 3: Ensure 'applicants' is a list
        applicants = record.get('applicants', [])
        if not isinstance(applicants, list):
            continue

        # Flatten the 1-to-many relationship
        for applicant in applicants:
            
            # SAFETY CHECK 4: Ensure 'applicant' is a dictionary
            if not isinstance(applicant, dict):
                continue
            
            # Append the row using the APPLICATION-LEVEL dates and times we extracted above
            rows.append({
                'Employee Name': applicant.get('name'),
                'NRIC': applicant.get('nric'),
                'Designation': applicant.get('designation'),
                'Company': company,
                'Purpose': purpose,
                'Start Date': start_date,
                'End Date': end_date,
                'Entering Time': entering_time,
                'Leaving Time': leaving_time
            })
            
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(rows)
    
    # Safely convert string dates to actual Datetime objects for math operations
    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df['End Date'] = pd.to_datetime(df['End Date'], errors='coerce')
    
    # Calculate Duration Days safely
    df['Duration Days'] = (df['End Date'] - df['Start Date']).dt.days + 1
    
    return df

# Load the dataframe
try:
    df = load_and_prepare_data('public_applications_2.json')
    with st.expander("Preview the Normalized Database"):
        st.dataframe(df)
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

# 4. Initialize Chat Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render past chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Core AI Interaction Logic
if prompt := st.chat_input("E.g., 'How many employees are from RT JAYA?'"):
    
    # Display user prompt in UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Force load the key from the environment
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        st.error("🚨 API Key not found! Please check your .env file.")
        st.stop()

    # Initialize the LLM (Using Gemini 1.5 Flash for speed)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0, google_api_key=api_key, max_retries = 5)
    
    # Create the Agent
    # allow_dangerous_code=True is required because the agent dynamically executes Python code
    agent = create_pandas_dataframe_agent(
        llm, 
        df, 
        verbose=True, 
        allow_dangerous_code=True,
        handle_parsing_errors=True
    )

    # Execute the query and display the response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing data and generating code..."):
            try:
                # 1. Create a hidden rule to force the AI to format its output
                formatting_rule = """
                
                IMPORTANT INSTRUCTIONS FOR YOUR FINAL ANSWER:
                - If the user asks for a list of items (like employee names), you MUST format your final answer as a clean Markdown table.
                - If the user asks for a count or a specific question, answer in a complete, polite sentence.
                - Do NOT just output raw python dictionaries or lists.
                """
                
                # 2. Combine the user's question with our hidden rule
                enhanced_prompt = prompt + formatting_rule

                # 3. Send the enhanced prompt to the agent
                response = agent.invoke(enhanced_prompt)
                answer = response["output"]
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
            except Exception as e:
                error_msg = f"I encountered an error analyzing that request: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})