import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import sqlite3
import plotly.express as px
from datetime import datetime

# Configuración inicial
st.set_page_config(page_title="Dashboard General", layout="wide")
st.title("Centro de Reportes del Sistema")

# Selección del tipo de reporte
opcion = st.selectbox(
    "Seleccione el tipo de reporte que desea visualizar:",
    ["Seleccionar...", "Reporte de Alarmas", "Reporte de Auditoría"]
)

# --- REPORTE DE ALARMAS ---
if opcion == "Reporte de Alarmas":
    st.header("Dashboard de Alarmas")
    uploaded_file = st.file_uploader("Seleccione el archivo CSV de Alarmas", type=["csv"], key="alarmas")

    if uploaded_file is not None:
        try:
            data = pd.read_csv(
                uploaded_file,
                encoding='latin1',
                skiprows=5,
                names=["Timestamp", "Tipo de Alarma", "Codigo de Alarma", "Mensaje"]
            )
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            st.stop()

        data = data[data["Timestamp"].str.contains(r"\d{2}-\d{2}-\d{4}", na=False)]
        data["Timestamp"] = pd.to_datetime(data["Timestamp"])
        data["Usuario"] = data["Mensaje"].str.extract(r"- por (.+)$", expand=True)
        data["Mensaje"] = data["Mensaje"].str.replace(r" - Por .+$", "", regex=True)
        data = data[data["Usuario"].notna() & (data["Usuario"].str.strip() != "") & (data["Usuario"].str.lower() != "none")]

        conn = sqlite3.connect("AlarmHistory.db")
        data.to_sql("Alarmas", conn, if_exists="replace", index=False)
        query_usuarios = """SELECT Usuario, COUNT(*) as Frecuencia FROM Alarmas GROUP BY Usuario ORDER BY Frecuencia DESC"""
        result_usuarios = pd.read_sql_query(query_usuarios, conn)
        conn.close()

        total_alarmas = len(data)
        alarmas_unicas = data["Mensaje"].dropna().unique()
        usuarios_unicos = data["Usuario"].dropna().unique()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Alarmas", total_alarmas)
        col2.metric("Tipos de Alarmas Únicas", len(alarmas_unicas))
        col3.metric("Usuarios Únicos", len(usuarios_unicos))

        st.subheader("Alarmas Únicas")
        st.dataframe(pd.DataFrame(alarmas_unicas, columns=["Alarmas Únicas"]))

        st.subheader("Usuarios Únicos")
        st.dataframe(pd.DataFrame(usuarios_unicos, columns=["Usuarios Únicos"]))

        st.subheader("Filtrar por Rango de Fechas")
        start_date, end_date = st.date_input(
            "Seleccione el rango de fechas:",
            [data["Timestamp"].min().date(), data["Timestamp"].max().date()],
            key="date_range_selector_alarmas"
        )
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        filtered_data = data[(data["Timestamp"] >= start_date) & (data["Timestamp"] <= end_date)]

        st.subheader("Lista Completa de Alarmas Filtradas")
        st.dataframe(filtered_data)

        st.subheader("Usuarios con Más Alarmas")
        fig_pie = px.pie(result_usuarios, names="Usuario", values="Frecuencia", title="Usuarios con Más Alarmas")
        st.plotly_chart(fig_pie)

        st.subheader("Distribución de Alarmas por Hora del Día")
        filtered_data["Hora"] = filtered_data["Timestamp"].dt.hour
        fig_hist = px.histogram(
            filtered_data, x="Hora", nbins=24,
            title="Histograma de Alarmas por Hora del Día",
            labels={"Hora": "Hora del Día", "count": "Cantidad de Alarmas"}
        )
        st.plotly_chart(fig_hist)

        st.subheader("Exportar Datos")
        st.download_button(
            label="Descargar Datos Filtrados (CSV)",
            data=filtered_data.to_csv(index=False).encode('utf-8'),
            file_name='datos_filtrados.csv',
            mime='text/csv'
        )

# --- REPORTE DE AUDITORÍA ---
elif opcion == "Reporte de Auditoría":
    st.header("Dashboard de Auditoría")
    uploaded_file = st.file_uploader("Seleccione el archivo CSV de Auditoría", type=["csv"], key="auditoria")

    if uploaded_file is not None:
        processed_data = [line.strip() for line in uploaded_file.read().decode('latin1').splitlines() if line.strip()]
        header_row = next((i for i, line in enumerate(processed_data) if 'Marca de tiempo' in line and 'Nodo' in line), None)

        if header_row is None:
            st.error("No se encontró el encabezado adecuado.")
            st.stop()

        header = processed_data[header_row].split(',')
        data_rows = [r.split(',') for r in processed_data[header_row + 1:] if len(r.split(',')) == len(header)]
        data = pd.DataFrame(data_rows, columns=header)
        data['Marca de tiempo'] = pd.to_datetime(data['Marca de tiempo'], errors='coerce')

        if "Usuario" in data.columns:
            data = data[data["Usuario"].notna() & (data["Usuario"].str.strip() != "") & (data["Usuario"].str.lower() != "none")]

        st.sidebar.header("Filtros de Fecha y Hora")
        start_date = st.sidebar.date_input("Fecha inicio", data['Marca de tiempo'].min().date())
        end_date = st.sidebar.date_input("Fecha fin", data['Marca de tiempo'].max().date())
        start_time = st.sidebar.time_input("Hora inicio", data['Marca de tiempo'].min().time())
        end_time = st.sidebar.time_input("Hora fin", data['Marca de tiempo'].max().time())
        start_dt = datetime.combine(start_date, start_time)
        end_dt = datetime.combine(end_date, end_time)

        filtered_data = data[(data['Marca de tiempo'] >= start_dt) & (data['Marca de tiempo'] <= end_dt)]
        filtered_data['Date'] = filtered_data['Marca de tiempo'].dt.date
        filtered_data['Hour'] = filtered_data['Marca de tiempo'].dt.hour

        st.header("Usuarios del Sistema")
        st.write("Usuarios activos:", filtered_data['Usuario'].unique())

        analog_changes = filtered_data[filtered_data['Texto'].str.contains("analógico", case=False, na=False)]
        digital_changes = filtered_data[filtered_data['Texto'].str.contains("digital", case=False, na=False)]

        st.subheader("Cambios Analógicos")
        st.write(analog_changes)

        st.subheader("Cambios Digitales")
        st.write(digital_changes)

        st.header("Comparativa de Cambios")
        change_types = {'Analógico': analog_changes.shape[0], 'Digital': digital_changes.shape[0]}
        plt.figure(figsize=(6, 4))
        plt.bar(change_types.keys(), change_types.values())
        st.pyplot(plt)

        representative_changes = filtered_data['Texto'].value_counts().head(10)
        plt.figure(figsize=(10, 5))
        plt.bar(representative_changes.index, representative_changes.values)
        plt.xticks(rotation=45)
        st.header("Cambios Más Frecuentes")
        st.pyplot(plt)

        user_changes = filtered_data['Usuario'].value_counts()
        plt.figure(figsize=(6, 6))
        plt.pie(user_changes, labels=user_changes.index, autopct='%1.1f%%')
        st.header("Cambios por Usuario")
        st.pyplot(plt)

        all_hours = list(range(24))
        heatmap_data = filtered_data.pivot_table(index='Date', columns='Hour', aggfunc='size', fill_value=0)
        heatmap_data = heatmap_data.reindex(columns=all_hours, fill_value=0)
        st.header("Actividad por Hora y Día")
        plt.figure(figsize=(14, 6))
        sns.heatmap(heatmap_data, cmap='coolwarm', annot=True, fmt="d")
        st.pyplot(plt)

        st.header("Alertas del Sistema")
        out_of_work_data = data[(data['Marca de tiempo'] < start_dt) | (data['Marca de tiempo'] > end_dt)]

        if not out_of_work_data.empty:
            st.warning(f"Eventos fuera del horario laboral: {len(out_of_work_data)}")

            if 'Texto' in out_of_work_data.columns:
                event_counts = out_of_work_data['Texto'].value_counts().head(10)
                plt.figure(figsize=(12, 6))
                sns.barplot(x=event_counts.index, y=event_counts.values)
                plt.xticks(rotation=45)
                st.subheader("Eventos fuera del horario")
                st.pyplot(plt)

        critical_keywords = ['error', 'fallo', 'alarma', 'crítico']
        critical_changes = filtered_data[filtered_data['Texto'].str.contains('|'.join(critical_keywords), case=False, na=False)]

        if not critical_changes.empty:
            st.error("Acciones críticas detectadas:")
            st.write(critical_changes)

        if 'Antiguo' in filtered_data.columns and 'Nuevo' in filtered_data.columns:
            try:
                filtered_data['Antiguo'] = pd.to_numeric(filtered_data['Antiguo'], errors='coerce')
                filtered_data['Nuevo'] = pd.to_numeric(filtered_data['Nuevo'], errors='coerce')
                out_of_range = filtered_data[(filtered_data['Nuevo'] < 0) | (filtered_data['Nuevo'] > 100)]
                if not out_of_range.empty:
                    st.error("Cambios fuera de rango detectados:")
                    st.write(out_of_range)
            except:
                st.info("No se pudieron analizar los cambios fuera de rango.")
