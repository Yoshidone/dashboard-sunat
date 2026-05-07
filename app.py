import streamlit as st
import pandas as pd
import zipfile
import io

st.set_page_config(page_title="CRUCE SUNAT vs SIRE", layout="wide")

st.title("📁 CRUCE SUNAT vs SIRE")
st.write("Convierte los TXT SIRE a Excel y luego cruza con SUNAT.")

# =====================================================
# FUNCION LIMPIAR
# =====================================================

def limpiar(valor):
    if pd.isna(valor):
        return ""

    return (
        str(valor)
        .replace(".0", "")
        .strip()
        .upper()
    )

# =====================================================
# OPCION DE CARGA
# =====================================================

tipo_carga = st.radio(
    "Selecciona carga SIRE",
    ["ZIP", "TXT"]
)

archivos_txt = []

# =====================================================
# SUBIR ZIP
# =====================================================

if tipo_carga == "ZIP":

    zip_file = st.file_uploader(
        "📦 Subir ZIP SIRE",
        type=["zip"]
    )

    if zip_file:

        with zipfile.ZipFile(zip_file, "r") as z:

            for nombre in z.namelist():

                if nombre.lower().endswith(".txt"):

                    contenido = z.read(nombre)
                    archivos_txt.append((nombre, contenido))

# =====================================================
# SUBIR TXT
# =====================================================

else:

    txt_files = st.file_uploader(
        "📂 Subir TXT SIRE",
        type=["txt"],
        accept_multiple_files=True
    )

    if txt_files:

        for archivo in txt_files:

            archivos_txt.append(
                (archivo.name, archivo.read())
            )

# =====================================================
# CONVERTIR TXT A DATAFRAMES
# =====================================================

dfs_sire = []

if archivos_txt:

    errores = 0

    for nombre_txt, contenido_txt in archivos_txt:

        try:

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
                engine="python"
            )

            # =====================================================
            # LIMPIAR COLUMNAS
            # =====================================================

            df.columns = [
                str(c).strip()
                for c in df.columns
            ]

            # =====================================================
            # VALIDAR COLUMNAS NECESARIAS
            # =====================================================

            columnas_necesarias = [
                "Nro Doc Identidad",
                "Serie del CDP",
                "Nro CP o Doc. Nro Inicial (Rango)"
            ]

            faltantes = [
                c for c in columnas_necesarias
                if c not in df.columns
            ]

            if faltantes:

                st.warning(
                    f"{nombre_txt}: faltan columnas {faltantes}"
                )

                continue

            # =====================================================
            # NORMALIZAR
            # =====================================================

            df["Nro Doc Identidad"] = (
                df["Nro Doc Identidad"]
                .astype(str)
                .apply(limpiar)
            )

            df["Serie del CDP"] = (
                df["Serie del CDP"]
                .astype(str)
                .apply(limpiar)
            )

            df["Nro CP o Doc. Nro Inicial (Rango)"] = (
                df["Nro CP o Doc. Nro Inicial (Rango)"]
                .astype(str)
                .apply(limpiar)
            )

            # =====================================================
            # CREAR KEY
            # =====================================================

            df["KEY"] = (
                df["Nro Doc Identidad"]
                + "_"
                + df["Serie del CDP"]
                + "_"
                + df["Nro CP o Doc. Nro Inicial (Rango)"]
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

            mes = "NO ENCONTRADO"

            try:

                periodo = nombre_txt[13:15]
                mes = mes_map.get(periodo, "NO ENCONTRADO")

            except:
                pass

            df["MES_ENCONTRADO"] = mes

            dfs_sire.append(df)

        except Exception as e:

            errores += 1

            st.warning(f"{nombre_txt}: {e}")

    # =====================================================
    # MENSAJE CONVERSION
    # =====================================================

    if len(dfs_sire) > 0:

        st.success(
            f"✅ {len(dfs_sire)} TXT convertidos correctamente a Excel."
        )

        st.info("📊 Ahora sube el archivo SUNAT.")

# =====================================================
# SUBIR SUNAT
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
        # NORMALIZAR SUNAT
        # =====================================================

        df_sunat["Número de documento Emisor"] = (
            df_sunat["Número de documento Emisor"]
            .astype(str)
            .apply(limpiar)
        )

        df_sunat["Número de Serie"] = (
            df_sunat["Número de Serie"]
            .astype(str)
            .apply(limpiar)
        )

        df_sunat["Número de Comprobante"] = (
            df_sunat["Número de Comprobante"]
            .astype(str)
            .apply(limpiar)
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
        # UNIR TODOS LOS SIRE
        # =====================================================

        df_sire_total = pd.concat(
            dfs_sire,
            ignore_index=True
        )

        # =====================================================
        # DICCIONARIO KEY -> MES
        # =====================================================

        diccionario_mes = dict(
            zip(
                df_sire_total["KEY"],
                df_sire_total["MES_ENCONTRADO"]
            )
        )

        # =====================================================
        # CRUCE
        # =====================================================

        df_sunat["MES_ENCONTRADO"] = (
            df_sunat["KEY"]
            .map(diccionario_mes)
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
            df_sunat,
            use_container_width=True
        )

        # =====================================================
        # DESCARGAR
        # =====================================================

        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df_sunat.to_excel(
                writer,
                index=False
            )

        st.download_button(
            "⬇ Descargar resultado Excel",
            data=output.getvalue(),
            file_name="CRUCE_SUNAT_SIRE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:

        st.error(f"❌ Error general: {e}")
