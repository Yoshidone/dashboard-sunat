import streamlit as st
import pandas as pd
import zipfile
import io
from io import BytesIO

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="CRUCE SUNAT vs SIRE",
    layout="wide"
)

st.title("📁 CRUCE SUNAT vs SIRE")

st.write(
    "Convierte los TXT SIRE a Excel y luego cruza con SUNAT."
)

# =====================================================
# FUNCIONES
# =====================================================

def limpiar(valor):

    if pd.isna(valor):
        return ""

    valor = str(valor)

    valor = valor.replace(".0", "")

    valor = valor.strip()

    return valor


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


def obtener_mes(nombre_archivo):

    for codigo, mes in MESES.items():

        if codigo in nombre_archivo:
            return mes

    return "SIN MES"


# =====================================================
# CARGA SIRE
# =====================================================

tipo_carga = st.radio(
    "Selecciona carga SIRE",
    ["ZIP", "TXT"]
)

archivos_txt = []

# =====================================================
# ZIP
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

                    archivos_txt.append(
                        (
                            nombre,
                            z.read(nombre)
                        )
                    )

# =====================================================
# TXT
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
                (
                    archivo.name,
                    archivo.getvalue()
                )
            )

# =====================================================
# VALIDAR TXT
# =====================================================

txt_convertidos = False

if len(archivos_txt) > 0:

    try:

        contador_txt = 0

        for nombre_txt, contenido_txt in archivos_txt:

            texto = contenido_txt.decode(
                "utf-8",
                errors="ignore"
            )

            pd.read_csv(
                io.StringIO(texto),
                sep="|",
                dtype=str,
                engine="python"
            )

            contador_txt += 1

        if contador_txt > 0:

            txt_convertidos = True

            st.success(
                f"✅ {contador_txt} TXT convertidos correctamente a Excel.\n\nAhora sube el archivo SUNAT."
            )

    except Exception as e:

        st.error(
            f"❌ Error convirtiendo TXT: {e}"
        )

# =====================================================
# SUNAT
# =====================================================

excel_sunat = None

if txt_convertidos:

    excel_sunat = st.file_uploader(
        "📊 Subir Excel SUNAT",
        type=["xlsx"]
    )

# =====================================================
# PROCESAR
# =====================================================

if archivos_txt and excel_sunat:

    try:

        lista_sire = []

        errores = []

        # =================================================
        # LEER TXT
        # =================================================

        for nombre_txt, contenido_txt in archivos_txt:

            try:

                mes = obtener_mes(nombre_txt)

                texto = contenido_txt.decode(
                    "utf-8",
                    errors="ignore"
                )

                # =========================================
                # TXT -> TABLA
                # =========================================

                df_txt = pd.read_csv(
                    io.StringIO(texto),
                    sep="|",
                    dtype=str,
                    engine="python"
                )

                # =========================================
                # LIMPIAR COLUMNAS
                # =========================================

                df_txt.columns = [

                    str(c)
                    .replace("\n", " ")
                    .strip()

                    for c in df_txt.columns

                ]

                # =========================================
                # ELIMINAR VACIAS
                # =========================================

                df_txt = df_txt.loc[
                    :,
                    ~df_txt.columns.str.contains("^Unnamed")
                ]

                # =========================================
                # LIMPIAR CELDAS
                # =========================================

                df_txt = df_txt.astype(str)

                for col in df_txt.columns:

                    df_txt[col] = (
                        df_txt[col]
                        .astype(str)
                        .str.strip()
                    )

                # =========================================
                # VALIDAR COLUMNAS
                # =========================================

                columnas_requeridas = [

                    "Nro Doc Identidad",

                    "Serie del CDP",

                    "Nro CP o Doc. Nro Inicial (Rango)"

                ]

                faltantes = [

                    c for c in columnas_requeridas

                    if c not in df_txt.columns

                ]

                if faltantes:

                    errores.append(
                        f"{nombre_txt}: faltan columnas {faltantes}"
                    )

                    continue

                # =========================================
                # LIMPIAR
                # =========================================

                df_txt["Nro Doc Identidad"] = (
                    df_txt["Nro Doc Identidad"]
                    .apply(limpiar)
                )

                df_txt["Serie del CDP"] = (
                    df_txt["Serie del CDP"]
                    .apply(limpiar)
                )

                df_txt["Nro CP o Doc. Nro Inicial (Rango)"] = (
                    df_txt["Nro CP o Doc. Nro Inicial (Rango)"]
                    .apply(limpiar)
                )

                # =========================================
                # KEY
                # =========================================

                df_txt["KEY"] = (

                    df_txt["Nro Doc Identidad"]

                    + "_"

                    + df_txt["Serie del CDP"]

                    + "_"

                    + df_txt["Nro CP o Doc. Nro Inicial (Rango)"]

                )

                # =========================================
                # MES
                # =========================================

                df_txt["MES_ENCONTRADO"] = mes

                # =========================================
                # GUARDAR
                # =========================================

                lista_sire.append(

                    df_txt[
                        [
                            "KEY",
                            "MES_ENCONTRADO"
                        ]
                    ]

                )

            except Exception as e:

                errores.append(
                    f"{nombre_txt}: {e}"
                )

        # =================================================
        # MOSTRAR ERRORES
        # =================================================

        for err in errores:

            st.warning(err)

        # =================================================
        # VALIDAR
        # =================================================

        if len(lista_sire) == 0:

            st.error(
                "❌ No se pudo convertir ningún TXT"
            )

            st.stop()

        # =================================================
        # UNIR SIRE
        # =================================================

        df_sire = pd.concat(
            lista_sire,
            ignore_index=True
        )

        # =================================================
        # ELIMINAR DUPLICADOS
        # =================================================

        df_sire = df_sire.drop_duplicates(
            subset=["KEY"]
        )

        # =================================================
        # LEER SUNAT
        # =================================================

        df_sunat = pd.read_excel(
            excel_sunat,
            dtype=str
        )

        # =================================================
        # LIMPIAR COLUMNAS
        # =================================================

        df_sunat.columns = [

            str(c)
            .replace("\n", " ")
            .strip()

            for c in df_sunat.columns

        ]

        # =================================================
        # LIMPIAR CELDAS
        # =================================================

        df_sunat = df_sunat.astype(str)

        for col in df_sunat.columns:

            df_sunat[col] = (
                df_sunat[col]
                .astype(str)
                .str.strip()
            )

        # =================================================
        # VALIDAR SUNAT
        # =================================================

        columnas_sunat = [

            "Número de documento Emisor",

            "Número de Serie",

            "Número de Comprobante"

        ]

        faltantes_sunat = [

            c for c in columnas_sunat

            if c not in df_sunat.columns

        ]

        if faltantes_sunat:

            st.error(
                f"❌ Faltan columnas SUNAT: {faltantes_sunat}"
            )

            st.stop()

        # =================================================
        # LIMPIAR
        # =================================================

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
        )

        # =================================================
        # KEY SUNAT
        # =================================================

        df_sunat["KEY"] = (

            df_sunat["Número de documento Emisor"]

            + "_"

            + df_sunat["Número de Serie"]

            + "_"

            + df_sunat["Número de Comprobante"]

        )

        # =================================================
        # CRUCE
        # =================================================

        df_final = df_sunat.merge(

            df_sire[
                [
                    "KEY",
                    "MES_ENCONTRADO"
                ]
            ],

            how="left",

            on="KEY"

        )

        # =================================================
        # COMPLETAR
        # =================================================

        df_final["MES_ENCONTRADO"] = (

            df_final["MES_ENCONTRADO"]

            .fillna("NO ENCONTRADO")

        )

        # =================================================
        # ELIMINAR KEY
        # =================================================

        df_final = df_final.drop(
            columns=["KEY"]
        )

        # =================================================
        # METRICAS
        # =================================================

        coincidencias = (

            df_final["MES_ENCONTRADO"]

            != "NO ENCONTRADO"

        ).sum()

        st.success(
            "✅ Cruce completado correctamente"
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "Total registros",
            len(df_final)
        )

        col2.metric(
            "Coincidencias",
            coincidencias
        )

        # =================================================
        # TABLA
        # =================================================

        st.dataframe(
            df_final,
            use_container_width=True,
            height=700
        )

        # =================================================
        # DESCARGAR
        # =================================================

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
