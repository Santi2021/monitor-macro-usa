import streamlit as st
import pandas as pd
from fredapi import Fred
import matplotlib.pyplot as plt

st.set_page_config(page_title="Monitor Macro USA", layout="wide")
st.title("🚀 Monitor Macro USA")

# API Key desde secrets
if 'FRED_API_KEY' in st.secrets:
    api_key = st.secrets['FRED_API_KEY']
    st.success("✅ API Key cargada")
else:
    st.error("❌ Configura FRED_API_KEY en Secrets")

if 'api_key' in locals():
    try:
        fred = Fred(api_key=api_key)
        
        with st.spinner("Descargando datos..."):
            unrate = fred.get_series('UNRATE', start='2020-01-01')
            
        st.metric("Tasa Desempleo", f"{unrate.iloc[-1]:.1f}%")
        
        fig, ax = plt.subplots()
        ax.plot(unrate.index, unrate.values, color='red', linewidth=2)
        ax.set_title("Tasa de Desempleo (UNRATE)")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        
        st.success("✅ ¡App funcionando!")
        
    except Exception as e:
        st.error(f"Error: {e}")
