import streamlit as st
import pandas as pd
from PIL import Image
from io import BytesIO

import database as db
from extractor import extract_directory

COLUMNS = [
    "empresa", "cargo", "nombre", "direccion",
    "codigo_postal", "ciudad", "telefono",
    "email", "web", "actividad", "seccion",
]

COLUMN_LABELS = {
    "empresa": "Empresa",
    "cargo": "Cargo",
    "nombre": "Nombre",
    "direccion": "Dirección",
    "codigo_postal": "C.P.",
    "ciudad": "Ciudad",
    "telefono": "Teléfono",
    "email": "Email",
    "web": "Web",
    "actividad": "Actividad",
    "seccion": "Sección",
}


def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    df_out = df.copy()
    df_out.columns = [COLUMN_LABELS.get(c, c) for c in df_out.columns]
    buf = BytesIO()
    df_out.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf.getvalue()


def main():
    st.set_page_config(
        page_title="Directorio Empresarial",
        page_icon="📇",
        layout="wide",
    )

    db.init_db()

    # ── Leer API key desde secrets ──────────────────────────────────
    api_key = ""
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass

    if not api_key:
        st.error("No se encontró la API Key. Configúrala en los Secrets de Streamlit Cloud.")
        st.stop()

    # ── Barra lateral ──────────────────────────────────────────────
    with st.sidebar:
        st.header("Configuración")

        modelo = st.selectbox(
            "Modelo de Gemini",
            options=[
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-2.5-pro",
            ],
            index=0,
            help="Si un modelo da error de cuota, prueba otro",
        )

        st.divider()

        saved = db.get_all_rows()
        st.metric("Registros guardados", len(saved))

        if saved:
            df_all = pd.DataFrame(saved).drop(
                columns=["id", "fecha_carga"], errors="ignore"
            )
            st.download_button(
                "Descargar todo en Excel",
                data=_df_to_excel_bytes(df_all),
                file_name="directorio_completo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

            st.divider()

            if st.button("Limpiar base de datos", use_container_width=True):
                db.clear_all()
                st.rerun()

    # ── Contenido principal ─────────────────────────────────────────
    st.title("Directorio Empresarial")
    st.caption("Extrae datos de contacto desde imágenes de revistas")

    # Paso 1 — Subir imagen
    st.subheader("Paso 1 · Subir imagen")
    uploaded = st.file_uploader(
        "Selecciona una imagen de la revista",
        type=["png", "jpg", "jpeg", "webp"],
        help="Sube una foto de una página del directorio",
    )

    if uploaded is None:
        st.session_state.pop("extracted_data", None)
        st.stop()

    image = Image.open(uploaded)

    with st.expander("Ver imagen cargada", expanded=False):
        st.image(image, use_container_width=True)

    # Detectar si cambiaron la imagen
    file_id = f"{uploaded.name}_{uploaded.size}"
    if st.session_state.get("_last_file_id") != file_id:
        st.session_state.pop("extracted_data", None)
        st.session_state["_last_file_id"] = file_id

    # Botón de extracción
    if st.button("Extraer datos de la imagen", type="primary", use_container_width=True):
        with st.spinner("Analizando imagen… esto puede tardar unos segundos"):
            try:
                data = extract_directory(image, api_key, model_name=modelo)
                st.session_state["extracted_data"] = data
                st.success(f"Se encontraron {len(data)} registros.")
            except Exception as exc:
                msg = str(exc)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    st.error(
                        "Cuota agotada para este modelo. "
                        "Prueba seleccionando otro modelo en la barra lateral, "
                        "o espera un minuto e inténtalo de nuevo."
                    )
                else:
                    st.error(f"Error al extraer datos: {exc}")

    # Paso 2 — Revisar
    if "extracted_data" not in st.session_state:
        st.stop()

    st.subheader("Paso 2 · Revisar y corregir")
    st.caption("Puedes editar cualquier celda. Usa los botones +/− de la tabla para agregar o eliminar filas.")

    df = pd.DataFrame(st.session_state["extracted_data"])
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS]

    edited_df = st.data_editor(
        df,
        column_config={
            col: st.column_config.TextColumn(label)
            for col, label in COLUMN_LABELS.items()
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
    )

    # Paso 3 — Confirmar
    st.subheader("Paso 3 · Confirmar")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Confirmar y guardar", type="primary", use_container_width=True):
            rows = edited_df.to_dict(orient="records")
            rows = [r for r in rows if any(str(v).strip() for v in r.values())]
            if rows:
                db.insert_rows(rows)
                st.session_state.pop("extracted_data", None)
                st.success(f"Se guardaron {len(rows)} registros.")
                st.rerun()
            else:
                st.warning("No hay datos para guardar.")

    with col2:
        st.download_button(
            "Descargar esta extracción en Excel",
            data=_df_to_excel_bytes(edited_df),
            file_name="extraccion_actual.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # ── Datos guardados ─────────────────────────────────────────────
    saved = db.get_all_rows()
    if saved:
        st.divider()
        st.subheader("Datos guardados")
        df_saved = pd.DataFrame(saved).drop(
            columns=["id", "fecha_carga"], errors="ignore"
        )
        df_display = df_saved.copy()
        df_display.columns = [COLUMN_LABELS.get(c, c) for c in df_display.columns]
        st.dataframe(df_display, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
