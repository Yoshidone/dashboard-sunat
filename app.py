import streamlit as st
import pandas as pd
import zipfile
import tempfile
import os
from io import BytesIO

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="CRUCE SUNAT vs SIRE",
    layout="wide"
)

st.title("📂 CRUCE SUNAT vs SIRE")

# =====================================================
# SUBIR ARCHIVOS
# =====================================================

zip_file = st.file_uploader(
    "📦 Subir ZIP SIRE",
    type=["zip"]
)

excel_file = st.file_uploader(
    "📊 Subir Excel SUNAT",
    type=["xlsx"]
)

# =====================================================
# FUNCION MES
# =====================================================

def obtener_mes_desde_txt(nombre_archivo):

    nombre_archivo = str(nombre_archivo)

    if "202501" in nombre_archivo:
        return "ENERO"

    elif "202502" in nombre_archivo:
        return "FEBRERO"

    elif "202503" in nombre_archivo:
        return "MARZO"

    elif "202504" in nombre_archivo:
        return "ABRIL"

    elif "202505" in nombre_archivo:
        return "MAYO"

    elif "202506" in nombre_archivo:
        return "JUNIO"

    elif "202507" in nombre_archivo:
        return "JULIO"

    elif "202508" in nombre_archivo:
        return "AGOSTO"

    elif "202509" in nombre_archivo:
        return "SEPTIEMBRE"

    elif "202510" in nombre_archivo:
        return "OCTUBRE"

    elif "202511" in nombre_archivo:
        return "NOVIEMBRE"

    elif "202512" in nombre_archivo:
        return "DICIEMBRE"

    return "NO ENCONTRADO"

# =====================================================
# PROCESAR
# =====================================================

if zip_file and excel_file:

    try:

        with st.spinner("Procesando archivos..."):

            # =====================================================
            # LEER EXCEL
            # =====================================================

            df_excel = pd.read_excel(
                excel_file,
                dtype=str
            )

            df_excel.columns = [
                str(c).strip()
                for c in df_excel.columns
            ]

            # =====================================================
            # LIMPIAR EXCEL
            # =====================================================

            df_excel["Nro Doc Identidad"] = (
                df_excel["Nro Doc Identidad"]
                .astype(str)
                .str.strip()
            )

            df_excel["Serie del CDP"] = (
                df_excel["Serie del CDP"]
                .astype(str)
                .str.strip()
            )

            df_excel["Nro CP o Doc. Nro Inicial (Rango)"] = (
                df_excel["Nro CP o Doc. Nro Inicial (Rango)"]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.strip()
            )

            # =====================================================
            # KEY EXCEL
            # =====================================================

            df_excel["KEY"] = (

                df_excel["Nro Doc Identidad"] + "_" +

                df_excel["Serie del CDP"] + "_" +

                df_excel["Nro CP o Doc. Nro Inicial (Rango)"]

            )

            # =====================================================
            # EXTRAER ZIP
            # =====================================================

            temp_dir = tempfile.mkdtemp()

            zip_path = os.path.join(
                temp_dir,
                "sire.zip"
            )

            with open(zip_path, "wb") as f:
                f.write(zip_file.getbuffer())

            with zipfile.ZipFile(
                zip_path,
                'r'
            ) as zip_ref:

                zip_ref.extractall(temp_dir)

            # =====================================================
            # DICCIONARIO MATCH
            # =====================================================

            mapa_match = {}

            # =====================================================
            # RECORRER TXT
            # =====================================================

            for root, dirs, files in os.walk(temp_dir):

                for file in files:

                    if file.endswith(".txt"):

                        ruta_txt = os.path.join(
                            root,
                            file
                        )

                        try:

                            df_txt = pd.read_csv(
                                ruta_txt,
                                sep="|",
                                dtype=str,
                                encoding="utf-8"
                            )

                            df_txt.columns = [
                                str(c).strip()
                                for c in df_txt.columns
                            ]

                            # =====================================================
                            # LIMPIAR TXT
                            # =====================================================

                            df_txt["Nro Doc Identidad"] = (
                                df_txt["Nro Doc Identidad"]
                                .astype(str)
                                .str.strip()
                            )

                            df_txt["Serie del CDP"] = (
                                df_txt["Serie del CDP"]
                                .astype(str)
                                .str.strip()
                            )

                            df_txt["Nro CP o Doc. Nro Inicial (Rango)"] = (
                                df_txt["Nro CP o Doc. Nro Inicial (Rango)"]
                                .astype(str)
                                .str.replace(r"\.0$", "", regex=True)
                                .str.strip()
                            )

                            # =====================================================
                            # KEY TXT
                            # =====================================================

                            df_txt["KEY"] = (

                                df_txt["Nro Doc Identidad"] + "_" +

                                df_txt["Serie del CDP"] + "_" +

                                df_txt["Nro CP o Doc. Nro Inicial (Rango)"]

                            )

                            # =====================================================
                            # MES
                            # =====================================================

                            mes = obtener_mes_desde_txt(file)

                            # =====================================================
                            # GUARDAR MATCH
                            # =====================================================

                            for key in df_txt["KEY"].unique():

                                if key not in mapa_match:

                                    mapa_match[key] = mes

                        except Exception as e:

                            st.warning(
                                f"Error leyendo {file}: {e}"
                            )

            # =====================================================
            # CRUCE FINAL
            # =====================================================

            df_excel["MES_ENCONTRADO"] = (
                df_excel["KEY"]
                .map(mapa_match)
            )

            df_excel["MES_ENCONTRADO"] = (
                df_excel["MES_ENCONTRADO"]
                .fillna("NO ENCONTRADO")
            )

            # =====================================================
            # ELIMINAR KEY
            # =====================================================

            df_excel = df_excel.drop(
                columns=["KEY"]
            )

            # =====================================================
            # METRICAS
            # =====================================================

            st.success("✅ Cruce completado correctamente")

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Total registros",
                    len(df_excel)
                )

            with col2:

                encontrados = (

                    df_excel["MES_ENCONTRADO"]

                    != "NO ENCONTRADO"

                ).sum()

                st.metric(
                    "Coincidencias",
                    encontrados
                )

            # =====================================================
            # MOSTRAR
            # =====================================================

            st.dataframe(
                df_excel,
                use_container_width=True,
                height=650
            )

            # =====================================================
            # EXPORTAR
            # =====================================================

            output = BytesIO()

            with pd.ExcelWriter(
                output,
                engine="openpyxl"
            ) as writer:

                df_excel.to_excel(
                    writer,
                    index=False,
                    sheet_name="CRUCE_FINAL"
                )

            output.seek(0)

            st.download_button(
                label="📥 DESCARGAR EXCEL FINAL",
                data=output,
                file_name="CRUCE_SUNAT_SIRE.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:

        st.error(f"❌ Error general: {e}")
