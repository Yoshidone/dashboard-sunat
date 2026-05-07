import streamlit as st
import pandas as pd
import zipfile
import tempfile
import os
from io import BytesIO

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="CRUCE SUNAT vs SIRE",
    layout="wide"
)

st.title("📂 CRUCE SUNAT vs SIRE")

st.markdown("""
Convierte automáticamente los TXT SIRE a tabla tipo Excel,
luego cruza:

SIRE:
- Nro Doc Identidad
- Serie del CDP
- Nro CP o Doc. Nro Inicial (Rango)

VS

SUNAT:
- Número de documento Emisor
- Número de Serie
- Número de Comprobante

y finalmente agrega:
MES_ENCONTRADO
""")

# =========================================================
# SUBIR ARCHIVOS
# =========================================================

modo = st.radio(
    "Selecciona carga SIRE",
    [
        "ZIP",
        "TXT"
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
        "📂 Subir TXT SIRE",
        type=["txt"],
        accept_multiple_files=True
    )

excel_file = st.file_uploader(
    "📊 Subir Excel SUNAT",
    type=["xlsx"]
)

# =========================================================
# FUNCION MES
# =========================================================

def obtener_mes(nombre):

    meses = {

        "202501": "ENERO",
        "202502": "FEBRERO",
        "202503": "MARZO",
        "202504": "ABRIL",
        "202505": "MAYO",
        "202506": "JUNIO",
        "202507": "JULIO",
        "202508": "AGOSTO",
        "202509": "SEPTIEMBRE",
        "202510": "OCTUBRE",
        "202511": "NOVIEMBRE",
        "202512": "DICIEMBRE"

    }

    for k, v in meses.items():

        if k in str(nombre):

            return v

    return "NO ENCONTRADO"

# =========================================================
# LIMPIAR
# =========================================================

def limpiar(valor):

    if pd.isna(valor):
        return ""

    valor = str(valor)

    valor = valor.replace(".0", "")
    valor = valor.replace("-", "")
    valor = valor.replace(" ", "")
    valor = valor.strip()
    valor = valor.upper()
    valor = valor.lstrip("0")

    return valor

# =========================================================
# PROCESAR
# =========================================================

if excel_file and (zip_file or txt_files):

    try:

        with st.spinner("Procesando archivos..."):

            # =====================================================
            # LEER SUNAT
            # =====================================================

            df_sunat = pd.read_excel(
                excel_file,
                dtype=str
            )

            df_sunat.columns = [
                str(c).strip()
                for c in df_sunat.columns
            ]

            # =====================================================
            # DETECTAR COLUMNAS SUNAT
            # =====================================================

            col_ruc = None
            col_serie = None
            col_comp = None

            for col in df_sunat.columns:

                nombre = str(col).lower()

                if (
                    "documento" in nombre
                    and "emisor" in nombre
                ):

                    col_ruc = col

                elif "serie" in nombre:

                    col_serie = col

                elif (
                    "comprobante" in nombre
                    and "tipo" not in nombre
                ):

                    col_comp = col

            # =====================================================
            # VALIDAR
            # =====================================================

            if col_ruc is None:
                st.error("No se encontró columna Número de documento Emisor")
                st.stop()

            if col_serie is None:
                st.error("No se encontró columna Número de Serie")
                st.stop()

            if col_comp is None:
                st.error("No se encontró columna Número de Comprobante")
                st.stop()

            # =====================================================
            # LIMPIAR SUNAT
            # =====================================================

            df_sunat["RUC_KEY"] = (
                df_sunat[col_ruc]
                .apply(limpiar)
            )

            df_sunat["SERIE_KEY"] = (
                df_sunat[col_serie]
                .apply(limpiar)
            )

            df_sunat["COMP_KEY"] = (
                df_sunat[col_comp]
                .apply(limpiar)
            )

            # =====================================================
            # KEY SUNAT
            # =====================================================

            df_sunat["KEY"] = (

                df_sunat["RUC_KEY"] + "_" +

                df_sunat["SERIE_KEY"] + "_" +

                df_sunat["COMP_KEY"]

            )

            # =====================================================
            # LISTA SIRE
            # =====================================================

            lista_sire = []

            # =====================================================
            # FUNCION TXT -> DATAFRAME
            # =====================================================

            def procesar_txt(nombre_archivo, contenido):

                try:

                    # =================================================
                    # TXT A TABLA
                    # =================================================

                    df_txt = pd.read_csv(
                        BytesIO(contenido),
                        sep="|",
                        dtype=str,
                        encoding="utf-8",
                        engine="python",
                        on_bad_lines="skip",
                        header=None
                    )

                    # =================================================
                    # VALIDAR COLUMNAS
                    # =================================================

                    if len(df_txt.columns) < 14:

                        st.warning(
                            f"{nombre_archivo} no tiene suficientes columnas"
                        )

                        return

                    # =================================================
                    # COLUMNAS REALES DEL TXT
                    # =================================================

                    columnas = {

                        8: "Serie del CDP",
                        10: "Nro CP o Doc. Nro Inicial (Rango)",
                        13: "Nro Doc Identidad"

                    }

                    df_txt = df_txt.rename(
                        columns=columnas
                    )

                    # =================================================
                    # LIMPIAR
                    # =================================================

                    df_txt["RUC_KEY"] = (
                        df_txt["Nro Doc Identidad"]
                        .apply(limpiar)
                    )

                    df_txt["SERIE_KEY"] = (
                        df_txt["Serie del CDP"]
                        .apply(limpiar)
                    )

                    df_txt["COMP_KEY"] = (
                        df_txt["Nro CP o Doc. Nro Inicial (Rango)"]
                        .apply(limpiar)
                    )

                    # =================================================
                    # KEY
                    # =================================================

                    df_txt["KEY"] = (

                        df_txt["RUC_KEY"] + "_" +

                        df_txt["SERIE_KEY"] + "_" +

                        df_txt["COMP_KEY"]

                    )

                    # =================================================
                    # MES
                    # =================================================

                    df_txt["MES_ENCONTRADO"] = (
                        obtener_mes(nombre_archivo)
                    )

                    # =================================================
                    # GUARDAR
                    # =================================================

                    lista_sire.append(

                        df_txt[
                            [
                                "KEY",
                                "MES_ENCONTRADO"
                            ]
                        ]

                    )

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

                            ruta = os.path.join(
                                root,
                                file
                            )

                            with open(
                                ruta,
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
            # VALIDAR SIRE
            # =====================================================

            if len(lista_sire) == 0:

                st.error(
                    "No se pudo leer información SIRE"
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
            # ELIMINAR DUPLICADOS
            # =====================================================

            df_sire = df_sire.drop_duplicates(
                subset=["KEY"]
            )

            # =====================================================
            # MAPA MATCH
            # =====================================================

            mapa_mes = (

                df_sire

                .set_index("KEY")[
                    "MES_ENCONTRADO"
                ]

                .to_dict()

            )

            # =====================================================
            # CRUCE
            # =====================================================

            df_sunat["MES_ENCONTRADO"] = (

                df_sunat["KEY"]

                .map(mapa_mes)

            )

            df_sunat["MES_ENCONTRADO"] = (

                df_sunat["MES_ENCONTRADO"]

                .fillna("NO ENCONTRADO")

            )

            # =====================================================
            # LIMPIAR COLUMNAS AUX
            # =====================================================

            df_sunat = df_sunat.drop(
                columns=[
                    "RUC_KEY",
                    "SERIE_KEY",
                    "COMP_KEY",
                    "KEY"
                ]
            )

            # =====================================================
            # METRICAS
            # =====================================================

            encontrados = (

                df_sunat["MES_ENCONTRADO"]

                != "NO ENCONTRADO"

            ).sum()

            st.success(
                "✅ Cruce completado correctamente"
            )

            c1, c2 = st.columns(2)

            with c1:

                st.metric(
                    "Total registros",
                    len(df_sunat)
                )

            with c2:

                st.metric(
                    "Coincidencias",
                    encontrados
                )

            # =====================================================
            # MOSTRAR
            # =====================================================

            st.dataframe(
                df_sunat,
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

                df_sunat.to_excel(
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
