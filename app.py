import streamlit as st
import pandas as pd
import zipfile
import io
from io import BytesIO

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="CRUCE SUNAT vs SIRE",
    layout="wide"
)

st.title("📁 CRUCE SUNAT vs SIRE")

st.write(
    "Cruza automáticamente los TXT SIRE con el Excel SUNAT y devuelve el MES donde fue encontrado."
)

# =========================================================
# LIMPIAR
# =========================================================

def limpiar(valor):

    if pd.isna(valor):
        return ""

    valor = str(valor).strip()

    if valor.endswith(".0"):
        valor = valor[:-2]

    return valor.strip()


# =========================================================
# LEER TXT SIRE
# =========================================================

def leer_txt_sire(contenido_bytes):

    texto = contenido_bytes.decode(
        "utf-8",
        errors="ignore"
    )

    df = pd.read_csv(
        io.StringIO(texto),
        sep="|",
        header=None,
        dtype=str,
        engine="python"
    )

    # eliminar columnas vacías
    df = df.dropna(axis=1, how="all")

    # columnas numéricas
    df.columns = range(df.shape[1])

    return df, None


# =========================================================
# MESES
# =========================================================

MESES = {
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
    "202512": "DICIEMBRE",
}


def extraer_mes(nombre_txt):

    for codigo, mes in MESES.items():

        if codigo in nombre_txt:
            return mes

    return "SIN MES"


# =========================================================
# CARGA SIRE
# =========================================================

tipo_carga = st.radio(
    "Selecciona carga SIRE",
    ["ZIP", "TXT"]
)

archivos_txt = []

# =========================================================
# ZIP
# =========================================================

if tipo_carga == "ZIP":

    zip_file = st.file_uploader(
        "📦 Subir ZIP SIRE",
        type=["zip"]
    )

    if zip_file:

        with zipfile.ZipFile(zip_file, "r") as z:

            for nombre in z.namelist():

                if nombre.lower().endswith(".txt"):

                    archivos_txt.append(
                        (
                            nombre,
                            z.read(nombre)
                        )
                    )

# =========================================================
# TXT
# =========================================================

else:

    txt_files = st.file_uploader(
        "📂 Subir TXT SIRE",
        type=["txt"],
        accept_multiple_files=True
    )

    if txt_files:

        for archivo in txt_files:

            archivos_txt.append(
                (
                    archivo.name,
                    archivo.getvalue()
                )
            )

# =========================================================
# SUBIR SUNAT
# =========================================================

excel_sunat = st.file_uploader(
    "📊 Subir Excel SUNAT",
    type=["xlsx"]
)

# =========================================================
# PROCESO
# =========================================================

if archivos_txt and excel_sunat:

    try:

        # =====================================================
        # LEER SUNAT
        # =====================================================

        df_sunat = pd.read_excel(
            excel_sunat,
            dtype=str
        )

        df_sunat.columns = [
            str(c).strip()
            for c in df_sunat.columns
        ]

        # =====================================================
        # COLUMNAS SUNAT
        # =====================================================

        col_ruc_sunat = "Número de documento Emisor"

        col_serie_sunat = "Número de Serie"

        col_comp_sunat = "Número de Comprobante"

        # =====================================================
        # KEY SUNAT
        # =====================================================

        df_sunat["_KEY"] = (

            df_sunat[col_ruc_sunat].apply(limpiar)

            + "_"

            + df_sunat[col_serie_sunat].apply(limpiar)

            + "_"

            + df_sunat[col_comp_sunat].apply(limpiar)

        )

        # =====================================================
        # POSICIONES TXT SIRE
        # =====================================================

        # M = Nro Doc Identidad
        IDX_RUC = 12

        # H = Serie del CDP
        IDX_SERIE = 7

        # J = Nro CP
        IDX_COMP = 9

        # =====================================================
        # DICCIONARIO MESES
        # =====================================================

        diccionario_mes = {}

        errores = []

        # =====================================================
        # RECORRER TXT
        # =====================================================

        for nombre_txt, contenido_txt in archivos_txt:

            try:

                mes = extraer_mes(nombre_txt)

                df_txt, error = leer_txt_sire(contenido_txt)

                if error:

                    errores.append(
                        f"{nombre_txt}: {error}"
                    )

                    continue

                # =============================================
                # CREAR KEY SIRE
                # =============================================

                df_txt["_KEY"] = (

                    df_txt[IDX_RUC].apply(limpiar)

                    + "_"

                    + df_txt[IDX_SERIE].apply(limpiar)

                    + "_"

                    + df_txt[IDX_COMP].apply(limpiar)

                )

                # =============================================
                # GUARDAR MES
                # =============================================

                for key in df_txt["_KEY"]:

                    if (
                        key
                        and key not in diccionario_mes
                    ):

                        diccionario_mes[key] = mes

            except Exception as e:

                errores.append(
                    f"{nombre_txt}: {e}"
                )

        # =====================================================
        # MOSTRAR ERRORES
        # =====================================================

        for err in errores:

            st.warning(err)

        # =====================================================
        # CRUCE
        # =====================================================

        df_sunat["MES_ENCONTRADO"] = (

            df_sunat["_KEY"]
            .map(diccionario_mes)
            .fillna("NO ENCONTRADO")

        )

        # =====================================================
        # CONTAR COINCIDENCIAS
        # =====================================================

        coincidencias = (
            df_sunat["MES_ENCONTRADO"]
            != "NO ENCONTRADO"
        ).sum()

        # =====================================================
        # RESULTADO
        # =====================================================

        st.success(
            "✅ Cruce completado correctamente"
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "Total registros",
            len(df_sunat)
        )

        col2.metric(
            "Coincidencias",
            coincidencias
        )

        # =====================================================
        # TABLA FINAL
        # =====================================================

        df_final = df_sunat.drop(
            columns=["_KEY"]
        )

        st.dataframe(
            df_final,
            use_container_width=True
        )

        # =====================================================
        # EXPORTAR
        # =====================================================

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df_final.to_excel(
                writer,
                index=False
            )

        st.download_button(
            "📥 Descargar Excel Final",
            data=output.getvalue(),
            file_name="CRUCE_SUNAT_SIRE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:

        st.error(
            f"❌ Error general: {e}"
        )
