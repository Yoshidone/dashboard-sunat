import streamlit as st
import pandas as pd
import zipfile
import io
import re

st.set_page_config(page_title="CRUCE SUNAT vs SIRE", layout="wide")

# =========================
# ESTILOS
# =========================
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
    font-weight: 700;
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

# =========================
# TITULO
# =========================
st.title("📁 CRUCE SUNAT vs SIRE")
st.write("Convierte los TXT SIRE y cruza con SUNAT.")

# =========================
# FUNCION EXTRAER CAR
# =========================
def extraer_car_desde_txt(contenido_txt):
    """
    Extrae el CAR del TXT SIRE.

    Busca patrones tipo:
    2055361851801F0010000011037
    """

    patron = r'(\d{11}[FB]\w+\d+)'

    encontrados = re.findall(patron, contenido_txt)

    return encontrados


# =========================
# CARGA SUNAT
# =========================
st.subheader("📄 Subir archivo SUNAT")

archivo_sunat = st.file_uploader(
    "Sube Excel SUNAT",
    type=["xlsx", "xls"]
)

df_sunat = None

if archivo_sunat:

    try:
        df_sunat = pd.read_excel(archivo_sunat)

        # LIMPIAR COLUMNAS
        df_sunat.columns = df_sunat.columns.str.strip()

        st.success("✅ Archivo SUNAT cargado correctamente")

        st.write("Columnas detectadas:")
        st.write(list(df_sunat.columns))

    except Exception as e:
        st.error(f"Error leyendo SUNAT: {e}")


# =========================
# CARGA SIRE
# =========================
st.subheader("📂 Selecciona carga SIRE")

tipo_carga = st.radio(
    "",
    ["ZIP", "TXT"]
)

txt_files = []

if tipo_carga == "ZIP":

    archivo_zip = st.file_uploader(
        "📦 Subir ZIP SIRE",
        type=["zip"]
    )

    if archivo_zip:

        zip_bytes = io.BytesIO(archivo_zip.read())

        with zipfile.ZipFile(zip_bytes, "r") as z:

            for nombre in z.namelist():

                if nombre.lower().endswith(".txt"):

                    txt_files.append({
                        "nombre": nombre,
                        "contenido": z.read(nombre).decode("latin-1", errors="ignore")
                    })

else:

    archivos_txt = st.file_uploader(
        "📁 Subir TXT SIRE",
        type=["txt"],
        accept_multiple_files=True
    )

    if archivos_txt:

        for archivo in archivos_txt:

            contenido = archivo.read().decode("latin-1", errors="ignore")

            txt_files.append({
                "nombre": archivo.name,
                "contenido": contenido
            })

# =========================
# PROCESAR MATCH
# =========================
if df_sunat is not None and len(txt_files) > 0:

    st.divider()

    # VALIDAR COLUMNA
    if "CAR SUNAT" not in df_sunat.columns:

        st.error("❌ No existe la columna 'CAR SUNAT' en el Excel.")

    else:

        resultados = []

        # NORMALIZAR
        df_sunat["CAR SUNAT"] = (
            df_sunat["CAR SUNAT"]
            .astype(str)
            .str.strip()
        )

        # =========================
        # RECORRER TXT
        # =========================
        for txt in txt_files:

            nombre_txt = txt["nombre"]
            contenido_txt = txt["contenido"]

            cars_txt = extraer_car_desde_txt(contenido_txt)

            if len(cars_txt) == 0:
                continue

            for car in cars_txt:

                # MATCH
                coincidencias = df_sunat[
                    df_sunat["CAR SUNAT"].astype(str) == str(car)
                ]

                if not coincidencias.empty:

                    for _, fila in coincidencias.iterrows():

                        fila_dict = fila.to_dict()

                        fila_dict["TXT ENCONTRADO"] = nombre_txt

                        resultados.append(fila_dict)

        # =========================
        # RESULTADO FINAL
        # =========================
        if len(resultados) > 0:

            df_resultado = pd.DataFrame(resultados)

            st.markdown("""
            <div class='success-box'>
            ✅ Se encontraron coincidencias entre SUNAT y SIRE
            </div>
            """, unsafe_allow_html=True)

            st.subheader("📊 Resultado Cruce")

            st.dataframe(
                df_resultado,
                use_container_width=True,
                height=600
            )

            # DESCARGA
            excel_buffer = io.BytesIO()

            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df_resultado.to_excel(writer, index=False)

            st.download_button(
                label="📥 Descargar Resultado Excel",
                data=excel_buffer.getvalue(),
                file_name="resultado_cruce_sunat_sire.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        else:

            st.markdown("""
            <div class='warning-box'>
            ⚠️ No se encontraron coincidencias.
            </div>
            """, unsafe_allow_html=True)
