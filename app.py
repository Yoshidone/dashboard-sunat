import streamlit as st
import pandas as pd
import zipfile
import io

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

st.write("""
1️⃣ Primero sube los TXT SIRE  
2️⃣ El sistema leerá el CAR SUNAT  
3️⃣ Luego sube el Excel SUNAT  
4️⃣ Se hará el match automáticamente
""")

# =========================================================
# FUNCION LEER TXT
# =========================================================
def leer_txt_sire(contenido, nombre_txt):

    registros = []

    lineas = contenido.splitlines()

    for linea in lineas:

        try:

            partes = linea.split("|")

            # VALIDAR
            if len(partes) < 5:
                continue

            # CAR SUNAT
            car = partes[3].strip()

            if car != "":

                registros.append({
                    "CAR_TXT": car,
                    "ARCHIVO_TXT": nombre_txt
                })

        except:
            pass

    return registros


# =========================================================
# FUNCION CREAR CAR SUNAT
# =========================================================
def crear_car(row):

    try:

        ruc = str(row["Número de documento Emisor"]).strip()

        serie = str(row["Número de Serie"]).strip().upper()

        comprobante = str(row["Número de Comprobante"]).strip()

        comprobante = comprobante.replace(".0", "")

        comprobante = comprobante.zfill(8)

        car = f"{ruc}{serie}{comprobante}"

        return car

    except:
        return ""


# =========================================================
# SUBIR TXT PRIMERO
# =========================================================
st.subheader("📂 PASO 1: Subir TXT SIRE")

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
# LEER TXT Y CREAR DF
# =========================================================
df_txt = pd.DataFrame()

if len(txt_files) > 0:

    lista_txt = []

    for txt in txt_files:

        nombre_txt = txt["nombre"]

        contenido_txt = txt["contenido"]

        registros = leer_txt_sire(
            contenido_txt,
            nombre_txt
        )

        lista_txt.extend(registros)

    df_txt = pd.DataFrame(lista_txt)

    if not df_txt.empty:

        st.markdown("""
        <div class='success-box'>
        ✅ TXT leídos correctamente
        </div>
        """, unsafe_allow_html=True)

        st.subheader("📊 CAR encontrados en TXT")

        st.dataframe(
            df_txt,
            use_container_width=True,
            height=300
        )

# =========================================================
# SUBIR SUNAT DESPUES
# =========================================================
if not df_txt.empty:

    st.divider()

    st.subheader("📄 PASO 2: Subir Excel SUNAT")

    archivo_sunat = st.file_uploader(
        "Sube archivo SUNAT",
        type=["xlsx", "xls"]
    )

    if archivo_sunat:

        try:

            df_sunat = pd.read_excel(archivo_sunat)

            df_sunat.columns = (
                df_sunat.columns.str.strip()
            )

            st.success("✅ Excel SUNAT cargado")

            # =================================================
            # VALIDAR COLUMNAS
            # =================================================
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

                st.error(f"""
                ❌ Faltan columnas:
                {faltantes}
                """)

            else:

                # =============================================
                # CREAR CAR_GENERADO
                # =============================================
                df_sunat["CAR_GENERADO"] = df_sunat.apply(
                    crear_car,
                    axis=1
                )

                # =============================================
                # MATCH
                # =============================================
                df_resultado = pd.merge(
                    df_sunat,
                    df_txt,
                    left_on="CAR_GENERADO",
                    right_on="CAR_TXT",
                    how="left"
                )

                # =============================================
                # ESTADO
                # =============================================
                df_resultado["MATCH"] = df_resultado[
                    "ARCHIVO_TXT"
                ].apply(
                    lambda x:
                    "ENCONTRADO"
                    if pd.notnull(x)
                    else "NO ENCONTRADO"
                )

                # =============================================
                # CONTADOR
                # =============================================
                encontrados = (
                    df_resultado["MATCH"]
                    == "ENCONTRADO"
                ).sum()

                st.markdown(f"""
                <div class='success-box'>
                ✅ Coincidencias encontradas:
                {encontrados}
                </div>
                """, unsafe_allow_html=True)

                # =============================================
                # RESULTADO
                # =============================================
                st.subheader("📊 Resultado Cruce")

                st.dataframe(
                    df_resultado,
                    use_container_width=True,
                    height=650
                )

                # =============================================
                # DESCARGAR
                # =============================================
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

        except Exception as e:

            st.error(f"❌ Error: {e}")
