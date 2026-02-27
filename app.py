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
st.markdown("Ask natural language questions about your `public_applications.json` dataset.")

# 3. Data Ingestion & Normalization
# We use st.cache_data so the system doesn't re-process the JSON on every chat interaction
@st.cache_data
def load_and_prepare_data(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    records = data.get('records', [])
    rows = []
    
    for record in records:
        app_info = record.get('application', {})
        if not app_info:
            continue
            
        datefrom = app_info.get('datefrom')
        dateto = app_info.get('dateto')
        company = app_info.get('company')
        purpose = app_info.get('purpose')
        
        # Flatten the 1-to-many relationship between applications and applicants
        for applicant in record.get('applicants', []):
            rows.append({
                'Employee Name': applicant.get('name'),
                'NRIC': applicant.get('nric'),
                'Designation': applicant.get('designation'),
                'Company': company,
                'Purpose': purpose,
                'Start Date': datefrom,
                'End Date': dateto
            })
            
    df = pd.DataFrame(rows)
    df = df.dropna(subset=['Start Date', 'End Date']).copy()
    df['Start Date'] = pd.to_datetime(df['Start Date'])
    df['End Date'] = pd.to_datetime(df['End Date'])
    df['Duration (Days)'] = (df['End Date'] - df['Start Date']).dt.days + 1
    return df

# Load the dataframe
try:
    df = load_and_prepare_data('public_applications.json')
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
        allow_dangerous_code=True 
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