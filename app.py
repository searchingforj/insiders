# app.py - Minimal version
import streamlit as st
from supabase import create_client
import pandas as pd

@st.cache_resource
def init_db():
    return create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])

st.title('SEC Form 4 J-Code Tracker')
db = init_db()

# Display latest filings
data = db.table('j_code_filings') \
         .select('*') \
         .order('filing_date', desc=True) \
         .limit(50) \
         .execute()

df = pd.DataFrame(data.data)
st.dataframe(df[['filing_date', 'ticker', 'company_name', 'filing_url']])
