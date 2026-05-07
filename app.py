import streamlit as st
import pandas as pd
import zipfile
import io
import re

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="CRUCE SUNAT vs SIRE",
    layout="wide"
)

# =====================================================
# TITULO
# =====================================================

st.title("📁 CRUCE SUNAT vs SIRE")

st.write(
    "Convierte los TXT SIRE a Excel y luego cruza con SUNAT."
)

# =====================================================
# FUNCIONES
# =====================================================

def limpiar_texto(valor):

    if pd.isna(valor):
        return ""

    valor = str(valor)

    valor = valor.strip()

    valor = valor.replace(".0", "")

    valor = valor.replace(" ", "")

    valor = valor.upper()

    return valor


def obtener_mes(nombre_archivo):

    meses = {
        "01": "ENERO",
        "02": "FEBRERO",
        "03": "MARZO",
        "04": "ABRIL",
        "05": "MAYO",
        "06": "JUNIO",
        "07": "JULIO",
        "08": "AGOSTO",
        "09": "SETIEMBRE",
        "10": "OCTUBRE",
        "11": "NOVIEMBRE",
        "12": "DICIEMBRE"
    }

    encontrado = re.search(r"2025(\d{2})", nombre_archivo)

    if encontrado:

        numero_mes = encontrado.group(1)

        return meses.get(numero_mes, "NO ENCONTRADO")

    return "NO ENCONTRADO"


def leer_txt_sire(contenido_txt, nombre_txt):

    texto = contenido_txt.decode(
        "utf-8",
        errors="ignore"
    )

    # =====================================================
    # LEER TXT
    # =====================================================

    df = pd.read_csv(

        io.StringIO(texto),

        sep="|",

        dtype=str,

        engine="python",

        skipinitialspace=True

    )

    # =====================================================
    # LIMPIAR COLUMNAS
    # =====================================================

    df.columns = [

        str(col).strip()

        for col in df.columns

    ]

    # =====================================================
    # LIMPIAR DATA
    # =====================================================

    for col in df.columns:

        df[col] = (

            df[col]
            .astype(str)
            .apply(limpiar_texto)

        )

    # =====================================================
    # CREAR KEY
    # =====================================================

    df["KEY"] = (

        df["Nro Doc Identidad"]
        .astype(str)
        .apply(limpiar_texto)

        + "_"

        + df["Serie del CDP"]
        .astype(str)
        .apply(limpiar_texto)

        + "_"

        + df["Nro CP o Doc. Nro Inicial (Rango)"]
        .astype(str)
        .apply(limpiar_texto)

    )

    # =====================================================
    # MES
    # =====================================================

    df["MES_ENCONTRADO"] = obtener_mes(nombre_txt)

    return df


# =====================================================
# TIPO CARGA
# =====================================================

tipo_carga = st.radio(

    "Selecciona carga SIRE",

    ["ZIP", "TXT"]

)

# =====================================================
# SUBIR TXT
# =====================================================

archivos_txt = []

if tipo_carga == "ZIP":

    archivo_zip = st.file_uploader(

        "📦 Subir ZIP SIRE",

        type=["zip"]

    )

    if archivo_zip:

        zip_data = zipfile.ZipFile(archivo_zip)

        for nombre in zip_data.namelist():

            if nombre.endswith(".txt"):

                contenido = zip_data.read(nombre)

                archivos_txt.append(
                    (nombre, contenido)
                )

else:

    archivos_subidos = st.file_uploader(

        "📂 Subir TXT SIRE",

        type=["txt"],

        accept_multiple_files=True

    )

    if archivos_subidos:

        for archivo in archivos_subidos:

            archivos_txt.append(
                (archivo.name, archivo.read())
            )

# =====================================================
# CONVERTIR TXT
# =====================================================

dfs_sire = []

if archivos_txt:

    errores = []

    for nombre_txt, contenido_txt in archivos_txt:

        try:

            df_sire = leer_txt_sire(
                contenido_txt,
                nombre_txt
            )

            dfs_sire.append(df_sire)

        except Exception as e:

            errores.append(
                f"{nombre_txt}: {str(e)}"
            )

    # =====================================================
    # MENSAJES
    # =====================================================

    if errores:

        for error in errores:

            st.warning(error)

    if dfs_sire:

        st.success(
            f"✅ {len(dfs_sire)} TXT convertidos correctamente a Excel."
        )

        st.info(
            "📊 Ahora sube el archivo SUNAT."
        )

# =====================================================
# SUBIR SUNAT
# =====================================================

archivo_sunat = st.file_uploader(

    "📊 Subir Excel SUNAT",

    type=["xlsx", "xls"]

)

# =====================================================
# CRUCE
# =====================================================

if archivo_sunat and dfs_sire:

    try:

        # =====================================================
        # LEER SUNAT
        # =====================================================

        df_sunat = pd.read_excel(

            archivo_sunat,

            dtype=str

        )

        # =====================================================
        # LIMPIAR COLUMNAS
        # =====================================================

        df_sunat.columns = [

            str(col).strip()

            for col in df_sunat.columns

        ]

        # =====================================================
        # LIMPIAR DATA
        # =====================================================

        columnas_sunat = [

            "Número de documento Emisor",

            "Número de Serie",

            "Número de Comprobante"

        ]

        for col in columnas_sunat:

            df_sunat[col] = (

                df_sunat[col]
                .astype(str)
                .apply(limpiar_texto)

            )

        # =====================================================
        # CREAR KEY SUNAT
        # =====================================================

        df_sunat["KEY"] = (

            df_sunat["Número de documento Emisor"]

            + "_"

            + df_sunat["Número de Serie"]

            + "_"

            + df_sunat["Número de Comprobante"]

        )

        # =====================================================
        # UNIR TODOS LOS TXT
        # =====================================================

        df_sire_total = pd.concat(

            dfs_sire,

            ignore_index=True

        )

        # =====================================================
        # DICCIONARIO
        # =====================================================

        diccionario_meses = dict(

            zip(

                df_sire_total["KEY"],

                df_sire_total["MES_ENCONTRADO"]

            )

        )

        # =====================================================
        # HACER MATCH
        # =====================================================

        df_sunat["MES_ENCONTRADO"] = (

            df_sunat["KEY"]

            .map(diccionario_meses)

            .fillna("NO ENCONTRADO")

        )

        # =====================================================
        # METRICAS
        # =====================================================

        coincidencias = (

            df_sunat["MES_ENCONTRADO"]

            != "NO ENCONTRADO"

        ).sum()

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
        # MOSTRAR RESULTADO
        # =====================================================

        st.dataframe(

            df_sunat,

            use_container_width=True

        )

        # =====================================================
        # DESCARGAR
        # =====================================================

        salida = io.BytesIO()

        with pd.ExcelWriter(

            salida,

            engine="openpyxl"

        ) as writer:

            df_sunat.to_excel(

                writer,

                index=False

            )

        st.download_button(

            "⬇ Descargar Excel Final",

            data=salida.getvalue(),

            file_name="CRUCE_FINAL.xlsx",

            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        )

    except Exception as e:

        st.error(f"❌ Error general: {e}")
