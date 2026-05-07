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
Cruza automáticamente los TXT SIRE con el Excel SUNAT
y devuelve el MES donde fue encontrado.
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

    for codigo, mes in meses.items():

        if codigo in str(nombre):

            return mes

    return "NO ENCONTRADO"

# =========================================================
# LIMPIAR
# =========================================================

def limpiar(valor):

    if pd.isna(valor):
        return ""

    valor = str(valor)

    # ============================================
    # CORREGIR NOTACION CIENTIFICA
    # ============================================

    if "E+" in valor.upper():

        try:

            valor = str(int(float(valor)))

        except:

            pass

    valor = valor.replace(".0", "")
    valor = valor.replace("-", "")
    valor = valor.replace(" ", "")
    valor = valor.replace("\n", "")
    valor = valor.replace("\r", "")

    valor = valor.strip().upper()

    return valor

# =========================================================
# MAIN
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

                # RUC
                if (
                    "documento" in nombre
                    and "emisor" in nombre
                ):

                    col_ruc = col

                # SERIE
                elif "serie" in nombre:

                    col_serie = col

                # COMPROBANTE
                elif (
                    "comprobante" in nombre
                    and "tipo" not in nombre
                ):

                    col_comp = col

            # =====================================================
            # VALIDAR
            # =====================================================

            if col_ruc is None:
                st.error("❌ No se encontró Número de documento Emisor")
                st.stop()

            if col_serie is None:
                st.error("❌ No se encontró Número de Serie")
                st.stop()

            if col_comp is None:
                st.error("❌ No se encontró Número de Comprobante")
                st.stop()

            # =====================================================
            # CREAR KEY SUNAT
            # =====================================================

            df_sunat["KEY"] = (

                df_sunat[col_ruc].apply(limpiar)

                + "_"

                + df_sunat[col_serie].apply(limpiar)

                + "_"

                + df_sunat[col_comp].apply(limpiar)

            )

            # =====================================================
            # LISTA SIRE
            # =====================================================

            lista_sire = []

            # =====================================================
            # FUNCION TXT
            # =====================================================

            def procesar_txt(nombre_archivo, contenido):

                try:

                    # =================================================
                    # LEER TXT
                    # =================================================

                    df_txt = pd.read_csv(
                        BytesIO(contenido),
                        sep="|",
                        header=None,
                        skiprows=1,
                        dtype=str,
                        encoding="utf-8",
                        engine="python",
                        on_bad_lines="skip"
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
                    # COLUMNAS REALES SIRE
                    # =================================================
                    #
                    # H = 8  = Serie del CDP
                    # J = 10 = Nro CP
                    # M = 13 = Nro Doc Identidad
                    #
                    # =================================================

                    df_txt = df_txt.rename(
                        columns={

                            8: "SERIE",
                            10: "COMP",
                            13: "RUC"

                        }
                    )

                    # =================================================
                    # CREAR KEY SIRE
                    # =====================================================

                    df_txt["KEY"] = (

                        df_txt["RUC"].apply(limpiar)

                        + "_"

                        + df_txt["SERIE"].apply(limpiar)

                        + "_"

                        + df_txt["COMP"].apply(limpiar)

                    )

                    # =================================================
                    # MES
                    # =====================================================

                    df_txt["MES_ENCONTRADO"] = (
                        obtener_mes(nombre_archivo)
                    )

                    # =================================================
                    # GUARDAR
                    # =====================================================

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
            # VALIDAR
            # =====================================================

            if len(lista_sire) == 0:

                st.error(
                    "❌ No se pudo leer información SIRE"
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
            # MAPA
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
            # ELIMINAR KEY
            # =====================================================

            df_sunat = df_sunat.drop(
                columns=["KEY"]
            )

            # =====================================================
            # METRICAS
            # =====================================================

            encontrados = (

                df_sunat["MES_ENCONTRADO"]

                != "NO ENCONTRADO"

            ).sum()

            st.success("✅ Cruce completado correctamente")

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
