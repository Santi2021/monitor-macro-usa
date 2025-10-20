import streamlit as st
import pandas as pd
import numpy as np
from fredapi import Fred
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuración de la página
st.set_page_config(
    page_title="Monitor Macro USA PRO",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🚀 Monitor Macro USA - Versión PRO")
st.markdown("---")

# Sidebar con controles
with st.sidebar:
    st.header("🎛️ Controles")
    
    if 'FRED_API_KEY' in st.secrets:
        api_key = st.secrets['FRED_API_KEY']
        st.success("✅ API Key configurada")
    else:
        st.error("❌ Configura FRED_API_KEY en Secrets")
        st.stop()
    
    fecha_inicio = st.selectbox(
        "Fecha de inicio:",
        ["2010-01-01", "2015-01-01", "2020-01-01"],
        index=0
    )
    
    tema = st.selectbox("Tema de gráficos:", ["plotly", "plotly_white", "plotly_dark"])

# Cache para datos FRED
@st.cache_data(ttl=3600)
def cargar_datos_fred(_fred, start_date):
    """Carga datos de FRED con manejo de errores"""
    
    # Series que SABEMOS que funcionan bien
    series_confiables = {
        # Laboral
        "UNRATE": "Tasa de Desempleo",
        
        # Inflación
        "CPIAUCSL": "CPI Total",
        "CPILFESL": "CPI Core",
        
        # Actividad
        "INDPRO": "Producción Industrial",
        "RSAFS": "Ventas Minoristas", 
        "HOUST": "Inicios Viviendas",
        
        # Tasas y Mercados
        "DGS10": "Tasa 10 años",
        "T10Y2Y": "Curva 10y-2y", 
        "VIXCLS": "VIX Volatilidad",
        "DGS2": "Tasa 2 años"
    }
    
    datos = {}
    errores = []
    
    for series_id, nombre in series_confiables.items():
        try:
            serie = _fred.get_series(series_id, start=start_date)
            if serie is not None and len(serie) > 0:
                datos[series_id] = serie
            else:
                errores.append(f"{nombre}: Sin datos")
        except Exception as e:
            errores.append(f"{nombre}: Error")
    
    # Mostrar errores en sidebar
    if errores:
        st.sidebar.warning(f"⚠️ {len(errores)} series con problemas")
    
    return pd.DataFrame(datos)

# Inicializar FRED
try:
    fred = Fred(api_key=api_key)
    
    with st.spinner("🔄 Cargando datos macroeconómicos..."):
        df = cargar_datos_fred(fred, fecha_inicio)
    
    if df.empty:
        st.error("❌ No se pudieron cargar datos")
        st.stop()
    
    # Calcular métricas solo para series con datos
    df_metrics = df.copy()
    for col in df.columns:
        serie_limpia = df[col].dropna()
        if len(serie_limpia) > 12:
            try:
                df_metrics[f'{col}_YoY'] = df[col].pct_change(periods=12) * 100
            except:
                pass  # Si falla, no hacemos nada
    
    st.success(f"✅ {len(df.columns)} series cargadas correctamente")
    
    # Mostrar series disponibles
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Series Disponibles")
    for col in df.columns:
        datos_serie = df[col].dropna()
        if len(datos_serie) > 0:
            ultimo_valor = datos_serie.iloc[-1]
            st.sidebar.write(f"• {col}: {ultimo_valor:.2f}")

    # PESTAÑAS
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Gráficos", "🔍 Análisis", "💾 Datos"])
    
    with tab1:
        st.header("📊 Dashboard Ejecutivo")
        
        # Métricas principales
        st.subheader("🎯 Indicadores Clave")
        cols = st.columns(4)
        
        metricas_config = {
            'UNRATE': {'format': '.1f', 'suffix': '%', 'umbral_bueno': 4.0, 'umbral_malo': 4.5},
            'CPILFESL': {'format': '.1f', 'suffix': '', 'es_index': True},
            'T10Y2Y': {'format': '.2f', 'suffix': 'pp', 'umbral_bueno': 0.5, 'umbral_malo': 0},
            'VIXCLS': {'format': '.1f', 'suffix': '', 'umbral_bueno': 15, 'umbral_malo': 20},
            'INDPRO': {'format': '.1f', 'suffix': '', 'es_index': True},
            'DGS10': {'format': '.2f', 'suffix': '%', 'umbral_bueno': 3.0, 'umbral_malo': 4.5}
        }
        
        metricas_mostradas = 0
        for i, (serie_id, config) in enumerate(metricas_config.items()):
            if serie_id in df.columns:
                with cols[metricas_mostradas % 4]:
                    datos_serie = df[serie_id].dropna()
                    if len(datos_serie) > 0:
                        valor_actual = datos_serie.iloc[-1]
                        
                        # Calcular delta si es posible
                        delta = None
                        if f'{serie_id}_YoY' in df_metrics.columns:
                            yoy_data = df_metrics[f'{serie_id}_YoY'].dropna()
                            if len(yoy_data) > 0:
                                delta = yoy_data.iloc[-1]
                        
                        # Determinar si es bueno/malo/neutral
                        if 'umbral_bueno' in config and 'umbral_malo' in config:
                            if valor_actual <= config['umbral_bueno']:
                                delta_color = "inverse" if serie_id in ['UNRATE', 'VIXCLS'] else "normal"
                            elif valor_actual >= config['umbral_malo']:
                                delta_color = "normal" if serie_id in ['UNRATE', 'VIXCLS'] else "inverse"
                            else:
                                delta_color = "off"
                        else:
                            delta_color = "off"
                        
                        st.metric(
                            label=serie_id,
                            value=f"{valor_actual:{config['format']}}{config.get('suffix', '')}",
                            delta=f"{delta:.1f}%" if delta is not None else None,
                            delta_color=delta_color
                        )
                        metricas_mostradas += 1
        
        # Gráfico de tendencias
        st.subheader("📈 Tendencias Principales")
        
        series_para_grafico = ['UNRATE', 'CPILFESL', 'T10Y2Y', 'VIXCLS']
        series_disponibles = [s for s in series_para_grafico if s in df.columns and len(df[s].dropna()) > 0]
        
        if series_disponibles:
            fig = go.Figure()
            
            for serie in series_disponibles:
                datos = df[serie].dropna()
                fig.add_trace(go.Scatter(
                    x=datos.index,
                    y=datos.values,
                    name=serie,
                    mode='lines'
                ))
            
            fig.update_layout(
                title="Evolución de Indicadores Clave",
                height=400,
                template=tema,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("📈 Gráficos Interactivos")
        
        # Selector de series
        series_disponibles = [col for col in df.columns if len(df[col].dropna()) > 0]
        
        if series_disponibles:
            series_seleccionadas = st.multiselect(
                "Seleccionar series:",
                series_disponibles,
                default=series_disponibles[:2]
            )
            
            if series_seleccionadas:
                fig = go.Figure()
                
                for serie in series_seleccionadas:
                    datos = df[serie].dropna()
                    fig.add_trace(go.Scatter(
                        x=datos.index,
                        y=datos.values,
                        name=serie,
                        mode='lines'
                    ))
                
                fig.update_layout(
                    title="Gráfico Personalizado",
                    height=500,
                    template=tema
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("👆 Selecciona series para graficar")
        else:
            st.warning("No hay series disponibles para graficar")
    
    with tab3:
        st.header("🔍 Análisis Detallado")
        
        if len(df.columns) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Estadísticas por Serie")
                serie_seleccionada = st.selectbox("Elegir serie:", df.columns)
                
                if serie_seleccionada:
                    datos = df[serie_seleccionada].dropna()
                    
                    if len(datos) > 0:
                        st.metric("Valor Actual", f"{datos.iloc[-1]:.2f}")
                        
                        col_stat1, col_stat2 = st.columns(2)
                        with col_stat1:
                            st.metric("Mínimo", f"{datos.min():.2f}")
                        with col_stat2:
                            st.metric("Máximo", f"{datos.max():.2f}")
            
            with col2:
                st.subheader("📅 Información del Dataset")
                st.write(f"**Series cargadas:** {len(df.columns)}")
                st.write(f"**Período:** {df.index[0].strftime('%b %Y')} - {df.index[-1].strftime('%b %Y')}")
                st.write(f"**Total datos:** {df.count().sum():,}")
    
    with tab4:
        st.header("💾 Datos Completos")
        st.dataframe(df, use_container_width=True, height=400)
        
        # Descarga
        csv = df.to_csv()
        st.download_button(
            "📥 Descargar CSV",
            csv,
            f"macro_datos_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

except Exception as e:
    st.error(f"❌ Error: {e}")

st.markdown("---")
st.caption(f"🕐 Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
