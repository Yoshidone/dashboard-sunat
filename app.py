import streamlit as st
import pandas as pd
import zipfile
import io
from io import BytesIO

st.set_page_config(page_title="CRUCE SUNAT vs SIRE", layout="wide")
st.title("📁 CRUCE SUNAT vs SIRE")
st.write("Cruza automáticamente los TXT SIRE con el Excel SUNAT y devuelve el MES donde fue encontrado.")

# =========================================================
# FUNCIÓN LIMPIAR
# =========================================================

def limpiar(valor):
    if pd.isna(valor):
        return ""
    valor = str(valor).strip()
    if valor.endswith(".0"):
        valor = valor[:-2]
    return valor.strip()

# =========================================================
# FUNCIÓN LEER TXT SIRE (ROBUSTA)
# =========================================================

def leer_txt_sire(contenido_bytes):
    """
    Lee un TXT del SIRE con separador |
    Busca la línea de encabezado real que contenga columnas conocidas.
    Retorna un DataFrame limpio o None si falla.
    """
    texto = contenido_bytes.decode("utf-8", errors="ignore")
    lineas = texto.splitlines()

    header_idx = None
    for i, linea in enumerate(lineas):
        # Buscar la línea que tiene los encabezados reales del SIRE
        if "Nro Doc Identidad" in linea or "Serie del CDP" in linea:
            header_idx = i
            break

    if header_idx is None:
        # Fallback: intentar leer desde el inicio y buscar columnas numéricamente
        return None, "No se encontró línea de encabezado con 'Nro Doc Identidad'"

    # Reconstruir el texto desde la línea del encabezado
    texto_limpio = "\n".join(lineas[header_idx:])

    df = pd.read_csv(
        io.StringIO(texto_limpio),
        sep="|",
        dtype=str,
        engine="python"
    )

    # Limpiar nombres de columnas
    df.columns = [str(c).strip() for c in df.columns]

    # Eliminar columnas Unnamed
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    return df, None

# =========================================================
# MESES
# =========================================================

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

def extraer_mes(nombre_txt):
    """
    Extrae el mes del nombre del archivo TXT.
    Ejemplo: LE2060239379920250100080400021112.txt → posición 13:19 → 202501 → ENERO
    También busca el patrón 2025XX en cualquier parte del nombre como fallback.
    """
    # Intento 1: posición fija 13:19
    if len(nombre_txt) >= 19:
        codigo = nombre_txt[13:19]
        if codigo in MESES:
            return MESES[codigo]

    # Intento 2: buscar cualquier coincidencia 2025XX en el nombre
    for codigo, mes in MESES.items():
        if codigo in nombre_txt:
            return mes

    return "SIN MES"

# =========================================================
# CARGA SIRE
# =========================================================

tipo_carga = st.radio("Selecciona tipo de carga SIRE", ["ZIP", "TXT"])

archivos_txt = []

if tipo_carga == "ZIP":
    zip_file = st.file_uploader("📦 Subir ZIP SIRE", type=["zip"])
    if zip_file:
        with zipfile.ZipFile(zip_file, "r") as z:
            for nombre in z.namelist():
                if nombre.lower().endswith(".txt"):
                    archivos_txt.append((nombre, z.read(nombre)))
else:
    txt_files = st.file_uploader(
        "📂 Subir TXT SIRE",
        type=["txt"],
        accept_multiple_files=True
    )
    if txt_files:
        for archivo in txt_files:
            archivos_txt.append((archivo.name, archivo.getvalue()))

# =========================================================
# CARGA SUNAT
# =========================================================

excel_sunat = st.file_uploader("📊 Subir Excel SUNAT", type=["xlsx"])

# =========================================================
# PROCESO PRINCIPAL
# =========================================================

if archivos_txt and excel_sunat:
    try:

        # -------------------------------------------------
        # LEER SUNAT
        # -------------------------------------------------

        df_sunat = pd.read_excel(excel_sunat, dtype=str)
        df_sunat.columns = [str(c).strip() for c in df_sunat.columns]

        col_ruc_sunat   = "Número de documento Emisor"
        col_serie_sunat = "Número de Serie"
        col_num_sunat   = "Número de Comprobante"

        # Verificar columnas requeridas
        faltantes = [c for c in [col_ruc_sunat, col_serie_sunat, col_num_sunat] if c not in df_sunat.columns]
        if faltantes:
            st.error(f"❌ El Excel SUNAT no tiene estas columnas: {faltantes}")
            st.stop()

        df_sunat["_KEY"] = (
            df_sunat[col_ruc_sunat].apply(limpiar)
            + "_"
            + df_sunat[col_serie_sunat].apply(limpiar)
            + "_"
            + df_sunat[col_num_sunat].apply(limpiar)
        )

        # -------------------------------------------------
        # LEER TODOS LOS TXT SIRE
        # -------------------------------------------------

        col_ruc_sire   = "Nro Doc Identidad"
        col_serie_sire = "Serie del CDP"
        col_num_sire   = "Nro CP o Doc. Nro Inicial (Rango)"

        diccionario_mes = {}
        errores = []

        for nombre_txt, contenido_txt in archivos_txt:

            mes = extraer_mes(nombre_txt)

            df_txt, error = leer_txt_sire(contenido_txt)

            if error:
                errores.append(f"{nombre_txt}: {error}")
                continue

            # Verificar columnas necesarias
            cols_faltantes = [c for c in [col_ruc_sire, col_serie_sire, col_num_sire] if c not in df_txt.columns]
            if cols_faltantes:
                # Intentar búsqueda parcial de columnas (por si hay espacios extra)
                mapa = {}
                for needed in [col_ruc_sire, col_serie_sire, col_num_sire]:
                    for col in df_txt.columns:
                        if needed.lower().strip() in col.lower().strip():
                            mapa[needed] = col
                            break

                if len(mapa) == 3:
                    df_txt = df_txt.rename(columns={v: k for k, v in mapa.items()})
                else:
                    errores.append(f"{nombre_txt}: columnas no encontradas → {cols_faltantes} | Columnas disponibles: {list(df_txt.columns)}")
                    continue

            # Construir KEY SIRE
            df_txt["_KEY"] = (
                df_txt[col_ruc_sire].apply(limpiar)
                + "_"
                + df_txt[col_serie_sire].apply(limpiar)
                + "_"
                + df_txt[col_num_sire].apply(limpiar)
            )

            # Registrar en diccionario (primera aparición gana)
            for key in df_txt["_KEY"]:
                if key and key not in diccionario_mes:
                    diccionario_mes[key] = mes

        # Mostrar errores si los hay
        for err in errores:
            st.warning(f"⚠️ {err}")

        # -------------------------------------------------
        # CRUCE
        # -------------------------------------------------

        df_sunat["MES_ENCONTRADO"] = (
            df_sunat["_KEY"]
            .map(diccionario_mes)
            .fillna("NO ENCONTRADO")
        )

        # -------------------------------------------------
        # RESULTADO
        # -------------------------------------------------

        coincidencias = (df_sunat["MES_ENCONTRADO"] != "NO ENCONTRADO").sum()

        st.success("✅ Cruce completado correctamente")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total registros SUNAT", len(df_sunat))
        col2.metric("Coincidencias encontradas", coincidencias)
        col3.metric("No encontrados", len(df_sunat) - coincidencias)

        # Tabla final sin columna interna _KEY
        df_final = df_sunat.drop(columns=["_KEY"])

        st.dataframe(df_final, use_container_width=True)

        # -------------------------------------------------
        # EXPORTAR
        # -------------------------------------------------

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_final.to_excel(writer, index=False)

        st.download_button(
            "📥 Descargar Excel Final",
            data=output.getvalue(),
            file_name="CRUCE_SUNAT_SIRE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Error general: {e}")
        st.exception(e)
