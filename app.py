import streamlit as st
import pandas as pd
import zipfile
import io
import re

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="CRUCE SUNAT vs SIRE",
    layout="wide"
)

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>

.main {
    background-color: #f8fafc;
}

.block-container {
    padding-top: 2rem;
}

h1 {
    color: #1e293b;
    font-weight: 800;
}

.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
}

.success-box {
    background: #dcfce7;
    padding: 15px;
    border-radius: 10px;
    color: #166534;
    font-weight: 600;
}

.warning-box {
    background: #fef9c3;
    padding: 15px;
    border-radius: 10px;
    color: #854d0e;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# TITULO
# =========================================================
st.title("📁 CRUCE SUNAT vs SIRE")

st.write("Convierte TXT SIRE y realiza cruce con archivo SUNAT.")

# =========================================================
# FUNCION EXTRAER CAR DESDE TXT
# =========================================================
def extraer_car_txt(texto):

    """
    Extrae CAR tipo:
    20553618518F001000011037
    """

    patron = r'(\d{11}[A-Z0-9]{1,10}\d{1,20})'

    encontrados = re.findall(patron, texto)

    return list(set(encontrados))


# =========================================================
# FUNCION CREAR CAR DESDE SUNAT
# =========================================================
def crear_car(row):

    try:

        ruc = str(row["Número de documento Emisor"]).strip()

        serie = str(row["Número de Serie"]).strip().upper()

        comprobante = str(row["Número de Comprobante"]).strip()

        # quitar .0 de excel
        comprobante = comprobante.replace(".0", "")

        # completar ceros
        comprobante = comprobante.zfill(8)

        car = f"{ruc}{serie}{comprobante}"

        return car

    except:
        return ""


# =========================================================
# SUBIR SUNAT
# =========================================================
st.subheader("📄 Subir Excel SUNAT")

archivo_sunat = st.file_uploader(
    "Sube archivo SUNAT",
    type=["xlsx", "xls"]
)

df_sunat = None

if archivo_sunat:

    try:

        df_sunat = pd.read_excel(archivo_sunat)

        # limpiar columnas
        df_sunat.columns = df_sunat.columns.str.strip()

        st.success("✅ Archivo SUNAT cargado")

        st.write("Columnas detectadas:")

        st.write(list(df_sunat.columns))

    except Exception as e:

        st.error(f"Error leyendo Excel: {e}")

# =========================================================
# SUBIR SIRE
# =========================================================
st.subheader("📂 Selecciona carga SIRE")

tipo_carga = st.radio(
    "",
    ["ZIP", "TXT"]
)

txt_files = []

# =========================================================
# ZIP
# =========================================================
if tipo_carga == "ZIP":

    archivo_zip = st.file_uploader(
        "📦 Subir ZIP",
        type=["zip"]
    )

    if archivo_zip:

        zip_bytes = io.BytesIO(archivo_zip.read())

        with zipfile.ZipFile(zip_bytes, "r") as z:

            for nombre in z.namelist():

                if nombre.lower().endswith(".txt"):

                    try:

                        contenido = z.read(nombre).decode(
                            "latin-1",
                            errors="ignore"
                        )

                        txt_files.append({
                            "nombre": nombre,
                            "contenido": contenido
                        })

                    except:
                        pass

# =========================================================
# TXT
# =========================================================
else:

    archivos_txt = st.file_uploader(
        "📁 Subir TXT",
        type=["txt"],
        accept_multiple_files=True
    )

    if archivos_txt:

        for archivo in archivos_txt:

            try:

                contenido = archivo.read().decode(
                    "latin-1",
                    errors="ignore"
                )

                txt_files.append({
                    "nombre": archivo.name,
                    "contenido": contenido
                })

            except:
                pass

# =========================================================
# PROCESAR
# =========================================================
if df_sunat is not None and len(txt_files) > 0:

    st.divider()

    columnas_necesarias = [
        "Número de documento Emisor",
        "Número de Serie",
        "Número de Comprobante"
    ]

    faltantes = [
        col for col in columnas_necesarias
        if col not in df_sunat.columns
    ]

    if len(faltantes) > 0:

        st.error(f"❌ Faltan columnas: {faltantes}")

    else:

        # =================================================
        # CREAR CAR DESDE SUNAT
        # =================================================
        df_sunat["CAR_GENERADO"] = df_sunat.apply(
            crear_car,
            axis=1
        )

        # normalizar
        df_sunat["CAR_GENERADO"] = (
            df_sunat["CAR_GENERADO"]
            .astype(str)
            .str.strip()
        )

        # =================================================
        # EXTRAER CAR DESDE TXT
        # =================================================
        lista_txt = []

        for txt in txt_files:

            nombre_txt = txt["nombre"]

            contenido_txt = txt["contenido"]

            cars = extraer_car_txt(contenido_txt)

            for car in cars:

                lista_txt.append({
                    "CAR_TXT": car.strip(),
                    "ARCHIVO_TXT": nombre_txt
                })

        # =================================================
        # DATAFRAME TXT
        # =================================================
        df_txt = pd.DataFrame(lista_txt)

        if df_txt.empty:

            st.warning("⚠️ No se encontraron CAR en los TXT")

        else:

            # =================================================
            # MATCH
            # =================================================
            df_resultado = pd.merge(
                df_sunat,
                df_txt,
                left_on="CAR_GENERADO",
                right_on="CAR_TXT",
                how="left"
            )

            # =================================================
            # ESTADO MATCH
            # =================================================
            df_resultado["MATCH"] = df_resultado[
                "ARCHIVO_TXT"
            ].apply(
                lambda x: "ENCONTRADO"
                if pd.notnull(x)
                else "NO ENCONTRADO"
            )

            # =================================================
            # RESULTADO
            # =================================================
            encontrados = (
                df_resultado["MATCH"] == "ENCONTRADO"
            ).sum()

            st.markdown(f"""
            <div class='success-box'>
            ✅ Coincidencias encontradas: {encontrados}
            </div>
            """, unsafe_allow_html=True)

            st.subheader("📊 Resultado Cruce")

            st.dataframe(
                df_resultado,
                use_container_width=True,
                height=650
            )

            # =================================================
            # DESCARGA EXCEL
            # =================================================
            excel_buffer = io.BytesIO()

            with pd.ExcelWriter(
                excel_buffer,
                engine="openpyxl"
            ) as writer:

                df_resultado.to_excel(
                    writer,
                    index=False
                )

            st.download_button(
                label="📥 Descargar Resultado Excel",
                data=excel_buffer.getvalue(),
                file_name="resultado_cruce_sunat_sire.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
