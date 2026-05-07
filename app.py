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

st.markdown("""
Cruza:

SIRE:
- Nro Doc Identidad
- Serie del CDP
- Nro CP o Doc. Nro Inicial (Rango)

VS

SUNAT:
- Número de documento Emisor
- Número de Serie
- Número de Comprobante

y agrega el MES donde fue encontrado.
""")

# =====================================================
# SUBIR ARCHIVOS
# =====================================================

modo = st.radio(
    "Selecciona cómo subir archivos SIRE:",
    [
        "ZIP",
        "CARPETA TXT"
    ]
)

zip_file = None
txt_files = None

if modo == "ZIP":

    zip_file = st.file_uploader(
        "📦 Subir ZIP SIRE",
        type=["zip"]
    )

else:

    txt_files = st.file_uploader(
        "📂 Subir TXT del SIRE",
        type=["txt"],
        accept_multiple_files=True
    )

excel_file = st.file_uploader(
    "📊 Subir Excel SUNAT",
    type=["xlsx"]
)

# =====================================================
# FUNCION MES
# =====================================================

def obtener_mes(nombre_archivo):

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

if excel_file and (zip_file or txt_files):

    try:

        with st.spinner("Procesando archivos..."):

            # =====================================================
            # LEER EXCEL SUNAT
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
            # DETECTAR COLUMNAS SUNAT
            # =====================================================

            col_ruc = None
            col_serie = None
            col_comprobante = None

            for col in df_excel.columns:

                nombre = str(col).lower()

                if "documento" in nombre and "emisor" in nombre:
                    col_ruc = col

                elif "serie" in nombre:
                    col_serie = col

                elif (
                    "comprobante" in nombre
                    and "tipo" not in nombre
                ):
                    col_comprobante = col

            # =====================================================
            # VALIDAR
            # =====================================================

            if col_ruc is None:
                st.error("No se encontró columna RUC")
                st.stop()

            if col_serie is None:
                st.error("No se encontró columna Serie")
                st.stop()

            if col_comprobante is None:
                st.error("No se encontró columna Comprobante")
                st.stop()

            # =====================================================
            # LIMPIAR SUNAT
            # =====================================================

            df_excel[col_ruc] = (
                df_excel[col_ruc]
                .astype(str)
                .str.strip()
                .str.lstrip("0")
            )

            df_excel[col_serie] = (
                df_excel[col_serie]
                .astype(str)
                .str.strip()
                .str.upper()
            )

            df_excel[col_comprobante] = (
                df_excel[col_comprobante]
                .astype(str)
                .str.replace(r"\.0$", "", regex=True)
                .str.replace("-", "")
                .str.strip()
                .str.lstrip("0")
            )

            # =====================================================
            # KEY SUNAT
            # =====================================================

            df_excel["KEY"] = (

                df_excel[col_ruc] + "_" +

                df_excel[col_serie] + "_" +

                df_excel[col_comprobante]

            )

            # =====================================================
            # MAPA MATCH
            # =====================================================

            mapa_match = {}

            # =====================================================
            # FUNCION PROCESAR TXT
            # =====================================================

            def procesar_txt(nombre_archivo, contenido):

                try:

                    lineas = contenido.decode(
                        "utf-8",
                        errors="ignore"
                    ).splitlines()

                    registros = []

                    for linea in lineas:

                        partes = linea.split("|")

                        # evitar líneas cortas
                        if len(partes) < 14:
                            continue

                        try:

                            # =====================================================
                            # CAMPOS REALES SIRE
                            # =====================================================

                            serie = (
                                str(partes[5])
                                .strip()
                                .upper()
                            )

                            numero = (
                                str(partes[7])
                                .replace(".0", "")
                                .replace("-", "")
                                .strip()
                                .lstrip("0")
                            )

                            ruc = (
                                str(partes[13])
                                .strip()
                                .lstrip("0")
                            )

                            # =====================================================
                            # VALIDAR
                            # =====================================================

                            if (
                                ruc == ""
                                or serie == ""
                                or numero == ""
                            ):
                                continue

                            # =====================================================
                            # CREAR KEY
                            # =====================================================

                            key = (

                                ruc + "_" +

                                serie + "_" +

                                numero

                            )

                            registros.append(key)

                        except:
                            pass

                    # =====================================================
                    # MES
                    # =====================================================

                    mes = obtener_mes(nombre_archivo)

                    # =====================================================
                    # GUARDAR MATCH
                    # =====================================================

                    for key in registros:

                        if key not in mapa_match:

                            mapa_match[key] = mes

                except Exception as e:

                    st.warning(
                        f"Error leyendo {nombre_archivo}: {e}"
                    )

            # =====================================================
            # ZIP
            # =====================================================

            if zip_file:

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

                for root, dirs, files in os.walk(temp_dir):

                    for file in files:

                        if file.endswith(".txt"):

                            ruta_txt = os.path.join(
                                root,
                                file
                            )

                            with open(
                                ruta_txt,
                                "rb"
                            ) as f:

                                contenido = f.read()

                            procesar_txt(
                                file,
                                contenido
                            )

            # =====================================================
            # TXT
            # =====================================================

            if txt_files:

                for archivo in txt_files:

                    procesar_txt(
                        archivo.name,
                        archivo.read()
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

            encontrados = (

                df_excel["MES_ENCONTRADO"]

                != "NO ENCONTRADO"

            ).sum()

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
                height=700
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
