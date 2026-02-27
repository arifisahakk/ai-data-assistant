# AI Application Data Assistant

This is an AI-powered data assistant built with Python and Streamlit. It uses LangChain and the Google Gemini API to analyze the `public_applications.json` dataset using natural language queries.

## How to Run this Project Locally

Because the `venv` (virtual environment) is not included in this repository, you will need to create a fresh one on your machine before running the app.

### Installation Steps

**1. Clone the repository**
Open your terminal and download the code:
```bash
git clone [https://github.com/arifisahakk/ai-data-assistant.git](https://github.com/arifisahakk/ai-data-assistant.git)
cd ai-data-assistant
```

**2. Create a virtual environment**
```bash
python -m venv venv
```

**3. Activate the virtual environment**

*For Windows systems:*
```powershell
.\venv\Scripts\activate
```

*For Mac/Linux systems:*
```bash
source venv/bin/activate
```

**4. Install the required dependencies**
With the virtual environment active, install the necessary libraries using the provided blueprint:
```bash
pip install -r requirements.txt
```

**5. Run the application**
```bash
streamlit run app.py
```

*(Note: The `.env` file containing the necessary API key is intentionally included in this repository for easy testing and review).*