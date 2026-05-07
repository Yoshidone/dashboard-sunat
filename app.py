import streamlit as st
import pandas as pd
import zipfile
import io
import os

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
1️⃣ Sube TXT, ZIP o carpeta completa  
2️⃣ El sistema leerá TODOS los CAR SUNAT  
3️⃣ Luego sube Excel SUNAT  
4️⃣ Se hará el match automáticamente
""")

# =========================================================
# FUNCION LEER TXT
# =========================================================
def leer_txt_sire(contenido, nombre_txt):

    registros = []

    try:

        lineas = contenido.splitlines()

        for linea in lineas:

            try:

                partes = linea.split("|")

                for valor in partes:

                    valor = str(valor).strip()

                    # VALIDAR CAR
                    if (
                        len(valor) >= 25
                        and valor[:11].isdigit()
                        and any(
                            letra in valor
                            for letra in ["F", "B", "E"]
                        )
                    ):

                        registros.append({
                            "CAR_TXT": valor,
                            "ARCHIVO_TXT": nombre_txt
                        })

            except:
                pass

    except:
        pass

    return registros


# =========================================================
# FUNCION CREAR CAR
# =========================================================
def crear_car(row):

    try:

        # RUC
        ruc = str(
            row["Número de documento Emisor"]
        ).strip()

        ruc = ruc.replace(".0", "")

        # TIPO
        tipo = str(
            row["Tipo de Comprobante"]
        ).strip()

        tipo = tipo.replace(".0", "")

        tipo = tipo.zfill(2)

        # SERIE
        serie = str(
            row["Número de Serie"]
        ).strip().upper()

        # COMPROBANTE
        comprobante = str(
            row["Número de Comprobante"]
        ).strip()

        comprobante = comprobante.replace(".0", "")

        comprobante = comprobante.zfill(10)

        # CAR
        car = f"{ruc}{tipo}{serie}{comprobante}"

        return str(car).strip()

    except:
        return ""


# =========================================================
# PASO 1
# =========================================================
st.subheader("📂 PASO 1: Subir TXT SIRE")

tipo_carga = st.radio(
    "Tipo de carga",
    [
        "TXT",
        "ZIP",
        "CARPETA COMPLETA"
    ]
)

txt_files = []

# =========================================================
# TXT
# =========================================================
if tipo_carga == "TXT":

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
# ZIP
# =========================================================
elif tipo_carga == "ZIP":

    archivo_zip = st.file_uploader(
        "📦 Subir ZIP",
        type=["zip"]
    )

    if archivo_zip:

        try:

            zip_bytes = io.BytesIO(
                archivo_zip.read()
            )

            with zipfile.ZipFile(
                zip_bytes,
                "r"
            ) as z:

                for nombre in z.namelist():

                    if nombre.lower().endswith(".txt"):

                        try:

                            contenido = z.read(
                                nombre
                            ).decode(
                                "latin-1",
                                errors="ignore"
                            )

                            txt_files.append({
                                "nombre": os.path.basename(nombre),
                                "contenido": contenido
                            })

                        except:
                            pass

        except Exception as e:

            st.error(f"Error ZIP: {e}")

# =========================================================
# CARPETA COMPLETA
# =========================================================
elif tipo_carga == "CARPETA COMPLETA":

    carpeta_txt = st.file_uploader(
        "📂 Subir carpeta completa",
        type=["txt"],
        accept_multiple_files=True
    )

    if carpeta_txt:

        for archivo in carpeta_txt:

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
# LEER TODOS LOS TXT
# =========================================================
df_txt = pd.DataFrame()

if len(txt_files) > 0:

    lista_txt = []

    progreso = st.progress(0)

    total = len(txt_files)

    for i, txt in enumerate(txt_files):

        nombre_txt = txt["nombre"]

        contenido_txt = txt["contenido"]

        registros = leer_txt_sire(
            contenido_txt,
            nombre_txt
        )

        lista_txt.extend(registros)

        progreso.progress((i + 1) / total)

    df_txt = pd.DataFrame(lista_txt)

    if not df_txt.empty:

        # LIMPIAR
        df_txt["CAR_TXT"] = (
            df_txt["CAR_TXT"]
            .astype(str)
            .str.strip()
        )

        # ELIMINAR DUPLICADOS
        df_txt = df_txt.drop_duplicates()

        # RESET
        df_txt = df_txt.reset_index(drop=True)

        st.markdown("""
        <div class='success-box'>
        ✅ TODOS los TXT fueron leídos correctamente
        </div>
        """, unsafe_allow_html=True)

        st.write(f"""
        📄 TXT procesados: {len(txt_files)}
        """)

        st.write(f"""
        🔎 Total CAR encontrados: {len(df_txt)}
        """)

        st.subheader("📊 CAR encontrados en TXT")

        st.dataframe(
            df_txt,
            use_container_width=True,
            height=450
        )

    else:

        st.markdown("""
        <div class='warning-box'>
        ⚠️ No se encontraron CAR válidos
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# PASO 2
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

            # LEER EXCEL
            df_sunat = pd.read_excel(
                archivo_sunat
            )

            # LIMPIAR COLUMNAS
            df_sunat.columns = (
                df_sunat.columns
                .str.strip()
            )

            st.success(
                "✅ Excel SUNAT cargado"
            )

            # VALIDAR
            columnas_necesarias = [
                "Número de documento Emisor",
                "Tipo de Comprobante",
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

                # CREAR CAR
                df_sunat["CAR_GENERADO"] = (
                    df_sunat.apply(
                        crear_car,
                        axis=1
                    )
                )

                # LIMPIAR
                df_sunat["CAR_GENERADO"] = (
                    df_sunat["CAR_GENERADO"]
                    .astype(str)
                    .str.strip()
                )

                # MATCH
                df_resultado = pd.merge(
                    df_sunat,
                    df_txt,
                    left_on="CAR_GENERADO",
                    right_on="CAR_TXT",
                    how="left"
                )

                # ESTADO
                df_resultado["MATCH"] = (
                    df_resultado[
                        "ARCHIVO_TXT"
                    ].apply(
                        lambda x:
                        "ENCONTRADO"
                        if pd.notnull(x)
                        else "NO ENCONTRADO"
                    )
                )

                # CONTADORES
                encontrados = (
                    df_resultado["MATCH"]
                    == "ENCONTRADO"
                ).sum()

                no_encontrados = (
                    df_resultado["MATCH"]
                    == "NO ENCONTRADO"
                ).sum()

                # MENSAJES
                st.markdown(f"""
                <div class='success-box'>
                ✅ Coincidencias encontradas:
                {encontrados}
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class='warning-box'>
                ⚠️ No encontrados:
                {no_encontrados}
                </div>
                """, unsafe_allow_html=True)

                # RESULTADO
                st.subheader("📊 Resultado Cruce")

                st.dataframe(
                    df_resultado,
                    use_container_width=True,
                    height=650
                )

                # DESCARGA
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
