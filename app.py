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

# Título principal con estilo
st.title("🚀 Monitor Macro USA - Versión PRO")
st.markdown("---")

# Sidebar con controles
with st.sidebar:
    st.header("🎛️ Controles")
    
    # API Key
    if 'FRED_API_KEY' in st.secrets:
        api_key = st.secrets['FRED_API_KEY']
        st.success("✅ API Key configurada")
    else:
        st.error("❌ Configura FRED_API_KEY en Secrets")
        st.stop()
    
    # Selector de fecha
    st.subheader("📅 Rango Temporal")
    fecha_inicio = st.selectbox(
        "Fecha de inicio:",
        ["2010-01-01", "2015-01-01", "2020-01-01", "2022-01-01"],
        index=0
    )
    
    # Selector de tema
    st.subheader("🎨 Personalización")
    tema = st.selectbox("Tema de gráficos:", ["plotly", "plotly_white", "plotly_dark"])
    
    st.markdown("---")
    st.caption("Desarrollado por Santi + DeepSeek")

# Cache para datos FRED (1 hora)
@st.cache_data(ttl=3600)
def cargar_datos_fred(_fred, start_date):
    """Carga todos los datos de FRED"""
    series_config = {
        # Laboral
        "UNRATE": "Tasa de Desempleo",
        "U6RATE": "Subempleo U6", 
        "JTSJOL": "Ofertas de Trabajo",
        
        # Inflación
        "CPIAUCSL": "CPI Total",
        "CPILFESL": "CPI Core", 
        "T10YIE": "Expectativas Inflación 10y",
        
        # Actividad
        "INDPRO": "Producción Industrial",
        "RSAFS": "Ventas Minoristas",
        "HOUST": "Inicios Viviendas",
        
        # Tasas y Mercados
        "DGS10": "Tasa 10 años", 
        "T10Y2Y": "Curva 10y-2y",
        "VIXCLS": "VIX Volatilidad"
    }
    
    datos = {}
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, (series_id, nombre) in enumerate(series_config.items()):
        try:
            progress_text.text(f"📡 Descargando {nombre}...")
            serie = _fred.get_series(series_id, start=start_date)
            datos[series_id] = serie
            progress_bar.progress((i + 1) / len(series_config))
        except Exception as e:
            st.sidebar.warning(f"⚠️ {nombre}: {e}")
    
    progress_text.empty()
    progress_bar.empty()
    
    return pd.DataFrame(datos)

# Inicializar FRED y cargar datos
try:
    fred = Fred(api_key=api_key)
    
    with st.spinner("🔄 Cargando datos macroeconómicos..."):
        df = cargar_datos_fred(fred, fecha_inicio)
    
    if df.empty:
        st.error("❌ No se pudieron cargar datos. Revisa tu API Key.")
        st.stop()
    
    # Calcular cambios anuales
    df_metrics = df.copy()
    for col in df.columns:
        if len(df[col].dropna()) > 12:
            df_metrics[f'{col}_YoY'] = df[col].pct_change(periods=12) * 100
    
    st.success(f"✅ {len(df.columns)} series cargadas desde {df.index[0].strftime('%b %Y')}")
    
    # PESTAÑAS PRINCIPALES
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📈 Gráficos", "🔍 Análisis", "💾 Datos"])
    
    with tab1:
        st.header("📊 Dashboard Ejecutivo")
        
        # Métricas en la parte superior
        st.subheader("🎯 Indicadores Clave")
        col1, col2, col3, col4 = st.columns(4)
        
        # Tasa de Desempleo
        with col1:
            if 'UNRATE' in df.columns:
                ultimo_unrate = df['UNRATE'].dropna().iloc[-1]
                st.metric(
                    "Tasa Desempleo", 
                    f"{ultimo_unrate:.1f}%",
                    delta=f"{df_metrics.get('UNRATE_YoY', pd.Series([0])).iloc[-1]:.1f}%" if 'UNRATE_YoY' in df_metrics.columns else None
                )
        
        # Inflación Core
        with col2:
            if 'CPILFESL_YoY' in df_metrics.columns:
                inflacion = df_metrics['CPILFESL_YoY'].dropna().iloc[-1]
                st.metric(
                    "Inflación Core (YoY)",
                    f"{inflacion:.1f}%",
                    delta="Alta" if inflacion > 3.0 else "Baja" if inflacion < 2.0 else "En target"
                )
        
        # Curva de Tasas
        with col3:
            if 'T10Y2Y' in df.columns:
                curva = df['T10Y2Y'].dropna().iloc[-1]
                st.metric(
                    "Curva 10y-2y",
                    f"{curva:.2f}pp",
                    delta="Invertida 🔴" if curva < 0 else "Normal 🟢" if curva > 0.5 else "Plana 🟡"
                )
        
        # VIX
        with col4:
            if 'VIXCLS' in df.columns:
                vix = df['VIXCLS'].dropna().iloc[-1]
                st.metric(
                    "VIX Volatilidad",
                    f"{vix:.1f}",
                    delta="Alto Miedo" if vix > 20 else "Calma" if vix < 15 else "Neutral"
                )
        
        # Gráfico rápido de tendencias
        st.subheader("📈 Tendencias Principales")
        
        series_rapidas = ['UNRATE', 'CPILFESL', 'T10Y2Y', 'VIXCLS']
        series_disponibles = [s for s in series_rapidas if s in df.columns]
        
        if series_disponibles:
            fig_tendencias = go.Figure()
            
            for serie in series_disponibles:
                datos_serie = df[serie].dropna()
                if len(datos_serie) > 0:
                    fig_tendencias.add_trace(
                        go.Scatter(
                            x=datos_serie.index,
                            y=datos_serie.values,
                            name=serie,
                            mode='lines'
                        )
                    )
            
            fig_tendencias.update_layout(
                title="Evolución de Indicadores Clave",
                height=400,
                template=tema,
                showlegend=True,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig_tendencias, use_container_width=True)
    
    with tab2:
        st.header("📈 Gráficos Interactivos")
        
        col_sel, col_opc = st.columns([2, 1])
        
        with col_sel:
            # Selector de series para graficar
            series_disponibles = [col for col in df.columns if len(df[col].dropna()) > 0]
            series_seleccionadas = st.multiselect(
                "Seleccionar series para graficar:",
                series_disponibles,
                default=series_disponibles[:3] if series_disponibles else []
            )
        
        with col_opc:
            # Opciones de visualización
            tipo_grafico = st.selectbox("Tipo de gráfico:", ["Línea", "Área"])
            mostrar_yoy = st.checkbox("Mostrar cambios YoY", value=False)
        
        if series_seleccionadas:
            fig = go.Figure()
            
            for serie in series_seleccionadas:
                datos = df_metrics[f'{serie}_YoY'].dropna() if mostrar_yoy and f'{serie}_YoY' in df_metrics.columns else df[serie].dropna()
                
                if len(datos) > 0:
                    if tipo_grafico == "Línea":
                        fig.add_trace(go.Scatter(
                            x=datos.index,
                            y=datos.values,
                            name=f"{serie} {'YoY' if mostrar_yoy else ''}",
                            mode='lines',
                            line=dict(width=2)
                        ))
                    else:  # Área
                        fig.add_trace(go.Scatter(
                            x=datos.index,
                            y=datos.values,
                            name=f"{serie} {'YoY' if mostrar_yoy else ''}",
                            mode='lines',
                            fill='tozeroy',
                            line=dict(width=1)
                        ))
            
            titulo = "Cambios Interanuales (YoY)" if mostrar_yoy else "Evolución de Indicadores"
            fig.update_layout(
                title=titulo,
                height=500,
                template=tema,
                showlegend=True,
                hovermode='x unified',
                xaxis=dict(title="Fecha"),
                yaxis=dict(title="Valor")
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("👆 Selecciona al menos una serie para graficar")
    
    with tab3:
        st.header("🔍 Análisis Detallado")
        
        col_izq, col_der = st.columns(2)
        
        with col_izq:
            st.subheader("📊 Estadísticas por Serie")
            
            serie_analisis = st.selectbox(
                "Seleccionar serie para análisis:",
                [col for col in df.columns if len(df[col].dropna()) > 0]
            )
            
            if serie_analisis:
                datos_serie = df[serie_analisis].dropna()
                
                if len(datos_serie) > 0:
                    # Métricas de la serie
                    st.metric("Valor Actual", f"{datos_serie.iloc[-1]:.2f}")
                    
                    col_stat1, col_stat2 = st.columns(2)
                    with col_stat1:
                        st.metric("Mínimo Histórico", f"{datos_serie.min():.2f}")
                    with col_stat2:
                        st.metric("Máximo Histórico", f"{datos_serie.max():.2f}")
                    
                    # Gráfico individual
                    fig_individual = px.line(
                        x=datos_serie.index, 
                        y=datos_serie.values,
                        title=f"{serie_analisis} - Evolución Individual"
                    )
                    fig_individual.update_layout(height=300)
                    st.plotly_chart(fig_individual, use_container_width=True)
        
        with col_der:
            st.subheader("🔗 Matriz de Correlaciones")
            
            # Calcular correlaciones
            df_numeric = df.select_dtypes(include=[np.number])
            if len(df_numeric.columns) > 1:
                corr_matrix = df_numeric.corr()
                
                fig_corr = px.imshow(
                    corr_matrix,
                    title="Correlación entre Indicadores",
                    color_continuous_scale="RdBu",
                    aspect="auto"
                )
                fig_corr.update_layout(height=400)
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("No hay suficientes datos para calcular correlaciones")
    
    with tab4:
        st.header("💾 Datos Completos")
        
        st.subheader("📋 Tabla de Datos")
        st.dataframe(df, use_container_width=True, height=400)
        
        st.subheader("📥 Exportación")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            # Descargar datos originales
            csv_original = df.to_csv()
            st.download_button(
                label="📊 Descargar Datos Originales (CSV)",
                data=csv_original,
                file_name=f"macro_datos_original_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col_exp2:
            # Descargar datos con métricas
            csv_metrics = df_metrics.to_csv()
            st.download_button(
                label="📈 Descargar Datos con Métricas (CSV)",
                data=csv_metrics,
                file_name=f"macro_datos_metricas_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        # Estadísticas del dataset
        st.subheader("📊 Información del Dataset")
        col_info1, col_info2, col_info3 = st.columns(3)
        
        with col_info1:
            st.metric("Total Series", len(df.columns))
        with col_info2:
            st.metric("Período Cubierto", f"{df.index[0].strftime('%b %Y')} - {df.index[-1].strftime('%b %Y')}")
        with col_info3:
            st.metric("Puntos de Datos", f"{df.count().sum():,}")

except Exception as e:
    st.error(f"❌ Error en la aplicación: {e}")
    st.info("💡 Verifica tu conexión y API Key de FRED")

# Footer
st.markdown("---")
st.caption(f"🕐 Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Monitor Macro USA v2.0 PRO")
