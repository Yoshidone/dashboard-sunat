import streamlit as st
import pandas as pd
import io
import zipfile

st.set_page_config(page_title="CRUCE SUNAT vs SIRE", layout="wide")

st.title("📁 CRUCE SUNAT vs SIRE")
st.write("Convierte los TXT SIRE y cruza con SUNAT.")

# =========================================================
# FUNCION LIMPIAR TEXTO
# =========================================================

def limpiar_texto(valor):
    if pd.isna(valor):
        return ""

    valor = str(valor)

    valor = valor.replace(".0", "")
    valor = valor.strip()
    valor = valor.upper()

    return valor


# =========================================================
# FUNCION LEER TXT SIRE
# =========================================================

def leer_txt_sire(archivo, nombre_archivo):

    contenido = archivo.read().decode("utf-8", errors="ignore")

    df = pd.read_csv(
        io.StringIO(contenido),
        sep="|",
        dtype=str,
        engine="python"
    )

    df.columns = [str(c).strip() for c in df.columns]

    # LIMPIAR COLUMNAS
    for col in df.columns:
        df[col] = df[col].astype(str).apply(limpiar_texto)

    # COLUMNAS NECESARIAS
    columnas_necesarias = [
        "NRO DOC IDENTIDAD",
        "TIPO CP/DOC.",
        "SERIE DEL CDP",
        "NRO CP O DOC. NRO INICIAL (RANGO)"
    ]

    for col in columnas_necesarias:
        if col not in df.columns:
            raise Exception(f"No existe columna: {col}")

    # COMPLETAR COMPROBANTE
    df["NRO CP O DOC. NRO INICIAL (RANGO)"] = (
        df["NRO CP O DOC. NRO INICIAL (RANGO)"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.zfill(10)
    )

    # CREAR MATCH
    df["MATCH"] = (
        df["NRO DOC IDENTIDAD"] +
        df["TIPO CP/DOC."] +
        df["SERIE DEL CDP"] +
        df["NRO CP O DOC. NRO INICIAL (RANGO)"]
    )

    # MES
    mes = nombre_archivo[12:18]

    df["MES_ENCONTRADO"] = mes

    return df[["MATCH", "MES_ENCONTRADO"]]


# =========================================================
# OPCIONES
# =========================================================

tipo_carga = st.radio(
    "Selecciona carga SIRE",
    ["ZIP", "TXT"]
)

# =========================================================
# SUBIR TXT
# =========================================================

archivos_txt = []

if tipo_carga == "TXT":

    archivos_txt = st.file_uploader(
        "📂 Subir TXT SIRE",
        type=["txt"],
        accept_multiple_files=True
    )

elif tipo_carga == "ZIP":

    archivo_zip = st.file_uploader(
        "📦 Subir ZIP",
        type=["zip"]
    )

    if archivo_zip:

        with zipfile.ZipFile(archivo_zip, "r") as z:

            for nombre in z.namelist():

                if nombre.endswith(".txt"):

                    contenido = z.read(nombre)

                    archivos_txt.append(
                        io.BytesIO(contenido)
                    )

# =========================================================
# CONVERTIR TXT
# =========================================================

df_sire_total = pd.DataFrame()

if archivos_txt:

    lista_df = []

    errores = []

    for archivo in archivos_txt:

        try:

            nombre_archivo = archivo.name

            df_temp = leer_txt_sire(
                archivo,
                nombre_archivo
            )

            lista_df.append(df_temp)

        except Exception as e:

            errores.append(
                f"{archivo.name}: {e}"
            )

    if errores:

        for err in errores:
            st.warning(err)

    if lista_df:

        df_sire_total = pd.concat(
            lista_df,
            ignore_index=True
        )

        st.success(
            f"✅ {len(lista_df)} TXT convertidos correctamente a Excel."
        )

        st.info(
            "📊 Ahora sube el archivo SUNAT."
        )

# =========================================================
# SUBIR SUNAT
# =========================================================

archivo_sunat = st.file_uploader(
    "📊 Subir Excel SUNAT",
    type=["xlsx", "xls"]
)

# =========================================================
# CRUCE
# =========================================================

if archivo_sunat and not df_sire_total.empty:

    try:

        df_sunat = pd.read_excel(
            archivo_sunat,
            dtype=str
        )

        # LIMPIAR COLUMNAS
        df_sunat.columns = [
            str(c).strip()
            for c in df_sunat.columns
        ]

        # LIMPIAR DATA
        for col in df_sunat.columns:
            df_sunat[col] = (
                df_sunat[col]
                .astype(str)
                .apply(limpiar_texto)
            )

        # VALIDAR COLUMNAS
        columnas_sunat = [
            "Número de documento Emisor",
            "Tipo de Comprobante",
            "Número de Serie",
            "Número de Comprobante"
        ]

        for col in columnas_sunat:

            if col not in df_sunat.columns:

                st.error(
                    f"Falta columna en SUNAT: {col}"
                )

                st.stop()

        # =====================================================
        # LIMPIAR COLUMNAS SUNAT
        # =====================================================

        df_sunat["Número de documento Emisor"] = (
            df_sunat["Número de documento Emisor"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        df_sunat["Tipo de Comprobante"] = (
            df_sunat["Tipo de Comprobante"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.zfill(2)
            .str.strip()
        )

        df_sunat["Número de Serie"] = (
            df_sunat["Número de Serie"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
            .str.upper()
        )

        df_sunat["Número de Comprobante"] = (
            df_sunat["Número de Comprobante"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
        )

        # convertir 13658987.0 -> 13658987
        df_sunat["Número de Comprobante"] = (
            df_sunat["Número de Comprobante"]
            .apply(
                lambda x: str(int(float(x)))
                if x.replace(".", "").isdigit()
                else x
            )
        )

        # =====================================================
        # CREAR MATCH SUNAT
        # =====================================================

        df_sunat["MATCH"] = (
            df_sunat["Número de documento Emisor"] +
            df_sunat["Tipo de Comprobante"] +
            df_sunat["Número de Serie"] +
            df_sunat["Número de Comprobante"].str.zfill(10)
        )

        # =====================================================
        # DICCIONARIO SIRE
        # =====================================================

        diccionario_sire = dict(
            zip(
                df_sire_total["MATCH"],
                df_sire_total["MES_ENCONTRADO"]
            )
        )

        # =====================================================
        # MATCH
        # =====================================================

        df_sunat["MES_ENCONTRADO"] = (
            df_sunat["MATCH"]
            .map(diccionario_sire)
        )

        df_sunat["MES_ENCONTRADO"] = (
            df_sunat["MES_ENCONTRADO"]
            .fillna("NO ENCONTRADO")
        )

        coincidencias = (
            df_sunat["MES_ENCONTRADO"]
            != "NO ENCONTRADO"
        ).sum()

        # =====================================================
        # RESULTADOS
        # =====================================================

        st.success("✅ Cruce completado correctamente")

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Total registros",
                len(df_sunat)
            )

        with col2:
            st.metric(
                "Coincidencias",
                coincidencias
            )

        st.dataframe(
            df_sunat,
            use_container_width=True
        )

        # DESCARGA
        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df_sunat.to_excel(
                writer,
                index=False
            )

        output.seek(0)

        st.download_button(
            "📥 Descargar resultado",
            data=output,
            file_name="resultado_cruce.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:

        st.error(f"❌ Error general: {e}")
