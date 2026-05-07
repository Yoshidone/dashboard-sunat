import streamlit as st
import pandas as pd
import zipfile
import io
from io import BytesIO

st.set_page_config(page_title="CRUCE SUNAT vs SIRE", layout="wide")

st.title("📁 CRUCE SUNAT vs SIRE")

st.write(
    "Cruza automáticamente los TXT SIRE con el Excel SUNAT y devuelve el MES donde fue encontrado."
)

# =========================================================
# FUNCION LIMPIAR
# =========================================================

def limpiar(valor):

    if pd.isna(valor):
        return ""

    valor = str(valor).strip()

    valor = valor.replace(".0", "")

    return valor


# =========================================================
# SELECCION
# =========================================================

tipo_carga = st.radio(
    "Selecciona carga SIRE",
    ["ZIP", "TXT"]
)

# =========================================================
# CARGA SIRE
# =========================================================

archivos_txt = []

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
# CARGA SUNAT
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

        df_sunat = pd.read_excel(excel_sunat)

        df_sunat.columns = [
            str(c).strip()
            for c in df_sunat.columns
        ]

        # =====================================================
        # CREAR KEY SUNAT
        # =====================================================

        df_sunat["KEY"] = (

            df_sunat["Número de documento Emisor"].apply(limpiar)

            + "_"

            + df_sunat["Número de Serie"].apply(limpiar)

            + "_"

            + df_sunat["Número de Comprobante"].apply(limpiar)

        )

        # =====================================================
        # LEER TODOS LOS TXT
        # =====================================================

        lista_sire = []

        for nombre_txt, contenido_txt in archivos_txt:

            try:

                # =============================================
                # MES
                # =============================================

                mes_numero = nombre_txt[13:19]

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

                mes = meses.get(mes_numero, "SIN MES")

                # =============================================
                # LEER TXT
                # =============================================

                texto = contenido_txt.decode(
                    "utf-8",
                    errors="ignore"
                )

                df_txt = pd.read_csv(
                    io.StringIO(texto),
                    sep="|",
                    dtype=str,
                    engine="python"
                )

                # =============================================
                # LIMPIAR COLUMNAS
                # =============================================

                df_txt.columns = [
                    str(c).strip()
                    for c in df_txt.columns
                ]

                # =============================================
                # CREAR KEY SIRE
                # =============================================

                df_txt["KEY"] = (

                    df_txt["Nro Doc Identidad"].apply(limpiar)

                    + "_"

                    + df_txt["Serie del CDP"].apply(limpiar)

                    + "_"

                    + df_txt["Nro CP o Doc. Nro Inicial (Rango)"].apply(limpiar)

                )

                # =============================================
                # MES
                # =============================================

                df_txt["MES_ENCONTRADO"] = mes

                lista_sire.append(
                    df_txt[["KEY", "MES_ENCONTRADO"]]
                )

            except Exception as e:

                st.warning(
                    f"Error leyendo {nombre_txt}: {e}"
                )

        # =====================================================
        # UNIR SIRE
        # =====================================================

        if len(lista_sire) > 0:

            df_sire_total = pd.concat(
                lista_sire,
                ignore_index=True
            )

        else:

            df_sire_total = pd.DataFrame(
                columns=["KEY", "MES_ENCONTRADO"]
            )

        # =====================================================
        # DICCIONARIO
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
        # COINCIDENCIAS
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

        # =====================================================
        # EXPORTAR
        # =====================================================

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df_sunat.drop(
                columns=["KEY"]
            ).to_excel(
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

        st.error(f"❌ Error general: {e}")
