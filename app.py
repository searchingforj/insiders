import streamlit as st
from supabase import create_client
import pandas as pd

# Initialize Supabase
@st.cache_resource
def init_supabase():
    return create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])

supabase = init_supabase()

st.title('Real-Time SEC Form 4 "J" Code Monitor')

# Display most recent filings
st.header('Recent J-Code Transactions')
st.caption('Updates every 10 minutes during SEC operating hours (6AM-10PM EST)')

# Get last 100 J-code filings
data = supabase.table('j_code_filings') \
    .select('filing_date, ticker, company_name, filing_url') \
    .order('filing_date', desc=True) \
    .limit(100) \
    .execute()

df = pd.DataFrame(data.data)

# Convert to clickable links
df['Filing'] = df['filing_url'].apply(lambda x: f'<a href="{x}" target="_blank">View Filing</a>')
df['Date Filed'] = pd.to_datetime(df['filing_date']).dt.strftime('%Y-%m-%d %H:%M')

# Display table without index
st.write(
    df[['Date Filed', 'ticker', 'company_name', 'Filing']].to_html(escape=False, index=False),
    unsafe_allow_html=True
)

# Auto-refresh every 10 minutes
st_autorefresh(interval=10 * 60 * 1000, key="data_refresh")
