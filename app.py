import streamlit as st
import pandas as pd
import zipfile
import io

st.set_page_config(page_title="CRUCE SUNAT vs SIRE", layout="wide")

st.title("📁 CRUCE SUNAT vs SIRE")

# =====================================================
# LIMPIAR
# =====================================================

def limpiar(x):

    if pd.isna(x):
        return ""

    return (
        str(x)
        .replace(".0", "")
        .strip()
        .upper()
    )

# =====================================================
# CARGA
# =====================================================

tipo = st.radio(
    "Selecciona carga SIRE",
    ["ZIP", "TXT"]
)

archivos_txt = []

if tipo == "ZIP":

    zip_file = st.file_uploader(
        "📦 Subir ZIP",
        type=["zip"]
    )

    if zip_file:

        with zipfile.ZipFile(zip_file, "r") as z:

            for nombre in z.namelist():

                if nombre.lower().endswith(".txt"):

                    archivos_txt.append(
                        (nombre, z.read(nombre))
                    )

else:

    txts = st.file_uploader(
        "📂 Subir TXT",
        type=["txt"],
        accept_multiple_files=True
    )

    if txts:

        for t in txts:

            archivos_txt.append(
                (t.name, t.read())
            )

# =====================================================
# LEER SIRE
# =====================================================

dfs_sire = []

if archivos_txt:

    for nombre_txt, contenido in archivos_txt:

        try:

            texto = contenido.decode(
                "utf-8",
                errors="ignore"
            )

            df = pd.read_csv(
                io.StringIO(texto),
                sep="|",
                dtype=str,
                engine="python"
            )

            df.columns = [
                str(c).strip()
                for c in df.columns
            ]

            # =====================================================
            # EXTRAER DESDE CAR SUNAT
            # =====================================================

            if "CAR SUNAT" not in df.columns:
                continue

            car = df["CAR SUNAT"].astype(str)

            # RUC
            df["RUC_SIRE"] = (
                car.str[0:11]
                .apply(limpiar)
            )

            # SERIE
            df["SERIE_SIRE"] = (
                car.str[13:17]
                .apply(limpiar)
            )

            # COMPROBANTE
            df["COMP_SIRE"] = (
                car.str[17:]
                .apply(limpiar)
                .str.lstrip("0")
            )

            # =====================================================
            # KEY
            # =====================================================

            df["KEY"] = (
                df["RUC_SIRE"]
                + "_"
                + df["SERIE_SIRE"]
                + "_"
                + df["COMP_SIRE"]
            )

            # =====================================================
            # MES
            # =====================================================

            mes_map = {
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

            mes = nombre_txt[13:15]

            df["MES_ENCONTRADO"] = mes_map.get(
                mes,
                "NO ENCONTRADO"
            )

            dfs_sire.append(df)

        except Exception as e:

            st.warning(f"{nombre_txt}: {e}")

    if len(dfs_sire) > 0:

        st.success(
            f"✅ {len(dfs_sire)} TXT convertidos correctamente."
        )

        st.info(
            "📊 Ahora sube el archivo SUNAT."
        )

# =====================================================
# SUNAT
# =====================================================

excel_sunat = st.file_uploader(
    "📊 Subir Excel SUNAT",
    type=["xlsx", "xls"]
)

# =====================================================
# CRUCE
# =====================================================

if excel_sunat and len(dfs_sire) > 0:

    try:

        df_sunat = pd.read_excel(
            excel_sunat,
            dtype=str
        )

        df_sunat.columns = [
            str(c).strip()
            for c in df_sunat.columns
        ]

        # =====================================================
        # LIMPIAR
        # =====================================================

        df_sunat["Número de documento Emisor"] = (
            df_sunat["Número de documento Emisor"]
            .apply(limpiar)
        )

        df_sunat["Número de Serie"] = (
            df_sunat["Número de Serie"]
            .apply(limpiar)
        )

        df_sunat["Número de Comprobante"] = (
            df_sunat["Número de Comprobante"]
            .apply(limpiar)
            .str.lstrip("0")
        )

        # =====================================================
        # KEY SUNAT
        # =====================================================

        df_sunat["KEY"] = (
            df_sunat["Número de documento Emisor"]
            + "_"
            + df_sunat["Número de Serie"]
            + "_"
            + df_sunat["Número de Comprobante"]
        )

        # =====================================================
        # UNIR SIRE
        # =====================================================

        df_sire_total = pd.concat(
            dfs_sire,
            ignore_index=True
        )

        # =====================================================
        # DICCIONARIO
        # =====================================================

        diccionario = dict(
            zip(
                df_sire_total["KEY"],
                df_sire_total["MES_ENCONTRADO"]
            )
        )

        # =====================================================
        # MATCH
        # =====================================================

        df_sunat["MES_ENCONTRADO"] = (
            df_sunat["KEY"]
            .map(diccionario)
            .fillna("NO ENCONTRADO")
        )

        # =====================================================
        # METRICAS
        # =====================================================

        coincidencias = (
            df_sunat["MES_ENCONTRADO"]
            != "NO ENCONTRADO"
        ).sum()

        st.success("✅ Cruce completado correctamente")

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
        # MOSTRAR
        # =====================================================

        st.dataframe(
            df_sunat.drop(columns=["KEY"]),
            use_container_width=True
        )

    except Exception as e:

        st.error(f"❌ Error general: {e}")
