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
st.markdown("Cruce por RUC + Serie + Número CP")

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
            # LEER TXT
            # =====================================================

            lista_sire = []

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
                            # OBTENER MES DESDE NOMBRE TXT
                            # =====================================================

                            nombre_archivo = str(file)

                            mes_txt = "NO ENCONTRADO"

                            if "202501" in nombre_archivo:
                                mes_txt = "ENERO"

                            elif "202502" in nombre_archivo:
                                mes_txt = "FEBRERO"

                            elif "202503" in nombre_archivo:
                                mes_txt = "MARZO"

                            elif "202504" in nombre_archivo:
                                mes_txt = "ABRIL"

                            elif "202505" in nombre_archivo:
                                mes_txt = "MAYO"

                            elif "202506" in nombre_archivo:
                                mes_txt = "JUNIO"

                            elif "202507" in nombre_archivo:
                                mes_txt = "JULIO"

                            elif "202508" in nombre_archivo:
                                mes_txt = "AGOSTO"

                            elif "202509" in nombre_archivo:
                                mes_txt = "SEPTIEMBRE"

                            elif "202510" in nombre_archivo:
                                mes_txt = "OCTUBRE"

                            elif "202511" in nombre_archivo:
                                mes_txt = "NOVIEMBRE"

                            elif "202512" in nombre_archivo:
                                mes_txt = "DICIEMBRE"

                            df_txt["MES_ENCONTRADO"] = mes_txt

                            lista_sire.append(df_txt)

                        except Exception as e:

                            st.warning(
                                f"Error leyendo {file}: {e}"
                            )

            # =====================================================
            # VALIDAR
            # =====================================================

            if len(lista_sire) == 0:

                st.error(
                    "No se encontraron TXT válidos"
                )

                st.stop()

            # =====================================================
            # UNIR SIRE
            # =====================================================

            df_sire = pd.concat(
                lista_sire,
                ignore_index=True
            )

            # =====================================================
            # LIMPIAR SIRE
            # =====================================================

            df_sire["Nro Doc Identidad"] = (
                df_sire["Nro Doc Identidad"]
                .astype(str)
                .str.strip()
            )

            df_sire["Serie del CDP"] = (
                df_sire["Serie del CDP"]
                .astype(str)
                .str.strip()
            )

            df_sire["Nro CP o Doc. Nro Inicial (Rango)"] = (
                df_sire["Nro CP o Doc. Nro Inicial (Rango)"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
            )

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
                .str.replace(".0", "", regex=False)
                .str.strip()
            )

            # =====================================================
            # CREAR KEY SIRE
            # =====================================================

            df_sire["KEY"] = (

                df_sire["Nro Doc Identidad"] + "_" +

                df_sire["Serie del CDP"] + "_" +

                df_sire["Nro CP o Doc. Nro Inicial (Rango)"]

            )

            # =====================================================
            # CREAR KEY EXCEL
            # =====================================================

            df_excel["KEY"] = (

                df_excel["Nro Doc Identidad"] + "_" +

                df_excel["Serie del CDP"] + "_" +

                df_excel["Nro CP o Doc. Nro Inicial (Rango)"]

            )

            # =====================================================
            # MAPA MES
            # =====================================================

            mapa_mes = (

                df_sire

                .drop_duplicates(subset=["KEY"])

                .set_index("KEY")["MES_ENCONTRADO"]

                .to_dict()

            )

            # =====================================================
            # CRUCE
            # =====================================================

            df_excel["MES_ENCONTRADO"] = (
                df_excel["KEY"]
                .map(mapa_mes)
            )

            # =====================================================
            # RELLENAR VACIOS
            # =====================================================

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
            # RESULTADOS
            # =====================================================

            st.success(
                "✅ Cruce completado correctamente"
            )

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
                label="📥 DESCARGAR CRUCE FINAL",
                data=output,
                file_name="CRUCE_SUNAT_SIRE.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:

        st.error(f"❌ Error general: {e}")
