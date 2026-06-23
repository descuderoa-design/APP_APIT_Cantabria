"""
Centro de Recursos APIT Cantabria
Recursos turísticos · Restaurantes · Experiencias
"""

import streamlit as st
import pandas as pd
from datetime import date
import requests
import re


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="APIT Cantabria",
    page_icon="logo_apit.png",
    layout="centered",
    initial_sidebar_state="collapsed",
)

SHEET_ID = "1J1T4vS736sotTVP9KgdSje0OxlBvFU_7alO4Mwap5YY"

URLS = {
    "recursos": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=recursos",
    "contenidos_recursos": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=contenidos-recursos",
    "restaurantes": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=restaurantes",
    "experiencias_restaurantes": f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=experiencias_restaurantes",
}

DIAS_ES = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}


# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────

def safe_key(texto: str) -> str:
    texto = str(texto).lower().strip()
    texto = re.sub(r"[^a-z0-9áéíóúñü]+", "_", texto)
    return texto.strip("_")


def limpiar(valor) -> str:
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def mensaje_error_envio():
    st.error(
        "No ha sido posible enviar la información. "
        "Inténtelo de nuevo más tarde o contacte con APIT Cantabria."
    )


# ─────────────────────────────────────────────
# ESTÉTICA
# ─────────────────────────────────────────────

def inject_css():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 760px;
            padding-top: 1.2rem;
            padding-bottom: 4rem;
        }

        .apit-header {
            text-align: center;
            padding: 1.1rem 0 0.9rem;
            margin-bottom: 0.8rem;
        }

        .apit-title {
            color: #004EA8;
            font-weight: 800;
            font-size: 1.55rem;
            margin: 0.35rem 0 0.1rem;
            letter-spacing: -0.02em;
        }

        .apit-subtitle {
            color: #4b5563;
            font-size: 0.9rem;
            margin-bottom: 0.15rem;
        }

        .apit-small {
            color: #6b7280;
            font-size: 0.76rem;
        }

        .section-header {
            background: linear-gradient(135deg, #004EA8 0%, #00843D 100%);
            color: white;
            padding: 0.75rem 1rem;
            border-radius: 12px;
            margin: 0.6rem 0 1rem;
            font-weight: 700;
            font-size: 1rem;
        }

        div[data-testid="stForm"] {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 0.85rem;
            background: #fbfdff;
        }

        .stButton button {
            border-radius: 8px;
        }

        .footer {
            text-align: center;
            color: #6b7280;
            font-size: 0.74rem;
            margin-top: 2rem;
            padding-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def cabecera():
    st.markdown('<div class="apit-header">', unsafe_allow_html=True)

    try:
        st.image("logo_apit.png", width=92)
    except Exception:
        st.markdown("### APIT")

    st.markdown(
        """
        <div class="apit-title">APIT Cantabria</div>
        <div class="apit-subtitle">Centro de Recursos para Guías Oficiales</div>
        <div class="apit-small">Recursos turísticos · Restaurantes · Experiencias</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# GOOGLE APPS SCRIPT
# ─────────────────────────────────────────────

def post_to_apps_script(payload: dict):
    payload["token"] = st.secrets["APPS_SCRIPT_TOKEN"]

    response = requests.post(
        st.secrets["APPS_SCRIPT_URL"],
        json=payload,
        timeout=10,
    )

    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError("Error de registro")

    return result


def save_incidencia(data: dict):
    payload = {
        "accion": "incidencia",
        "usuario_nombre": data["usuario_nombre"],
        "tipo": data["tipo"],
        "categoria": data["categoria"],
        "nombre": data["nombre"],
        "municipio": data.get("municipio", ""),
        "asunto": data["asunto"],
        "descripcion": data["descripcion"],
    }

    return post_to_apps_script(payload)


def save_resena_restaurante(data: dict):
    payload = {
        "accion": "nueva_resena_restaurante",
        "restaurante": data["restaurante"],
        "fecha": data["fecha"],
        "guia": data["guia"],
        "num_personas": data["num_personas"],
        "precio_por_persona": data["precio_por_persona"],
        "rating": data["rating"],
        "comentario": data["comentario"],
    }

    return post_to_apps_script(payload)


# ─────────────────────────────────────────────
# DATOS
# ─────────────────────────────────────────────

@st.cache_data(ttl=600)
def load_data():
    dfs = {}

    for key, url in URLS.items():
        df = pd.read_csv(url)

        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )

        for col in [
            "fecha_inicio",
            "fecha_fin",
            "actualizado",
            "ultima_actualizacion",
            "fecha",
        ]:
            if col in df.columns:
                df[col] = pd.to_datetime(
                    df[col],
                    dayfirst=True,
                    errors="coerce",
                )

        dfs[key] = df

    return dfs


def fila_es_fecha(row: pd.Series, fecha: date) -> bool:
    inicio = row.get("fecha_inicio")
    fin = row.get("fecha_fin")

    if pd.notna(inicio) and fecha < inicio.date():
        return False

    if pd.notna(fin) and fecha > fin.date():
        return False

    dias_str = str(row.get("dias_semana", "") or "").strip()

    if dias_str:
        dia = DIAS_ES[fecha.weekday()]
        dias = [d.strip().lower() for d in dias_str.split("-")]

        if dia not in dias:
            return False

    return True


def filtrar_contenido(df: pd.DataFrame, recurso: str, fecha: date) -> pd.DataFrame:
    if "recurso" not in df.columns:
        return pd.DataFrame()

    sub = df[df["recurso"] == recurso].copy()

    if sub.empty:
        return sub

    mask = sub.apply(lambda r: fila_es_fecha(r, fecha), axis=1)
    return sub[mask]


# ─────────────────────────────────────────────
# FORMULARIOS
# ─────────────────────────────────────────────

def formulario_incidencia(tipo, categoria, nombre, municipio=""):
    form_key = f"form_incidencia_{safe_key(tipo)}_{safe_key(categoria)}_{safe_key(nombre)}"

    with st.expander("Reportar dato incorrecto", expanded=False):
        with st.form(form_key):
            guia = st.text_input(
                "Nombre del guía",
                placeholder="Nombre y apellidos",
                key=f"guia_{form_key}",
            )

            descripcion = st.text_area(
                "¿Qué dato es incorrecto o falta?",
                placeholder="Indique brevemente qué información debe corregirse o completarse.",
                key=f"descripcion_{form_key}",
            )

            enviar = st.form_submit_button("Enviar")

            if enviar:
                if not guia.strip():
                    st.warning("Indique su nombre.")
                    return

                if not descripcion.strip():
                    st.warning("Describa brevemente el problema.")
                    return

                try:
                    save_incidencia({
                        "usuario_nombre": guia,
                        "tipo": tipo,
                        "categoria": categoria,
                        "nombre": nombre,
                        "municipio": municipio,
                        "asunto": f"Corrección de {tipo}: {nombre}",
                        "descripcion": descripcion,
                    })

                    st.success(
                        "Gracias. La información ha sido registrada "
                        "y será revisada por APIT Cantabria."
                    )

                except Exception:
                    mensaje_error_envio()


def formulario_nuevo_recurso():
    with st.expander("Proponer nuevo recurso turístico", expanded=False):
        with st.form("form_nuevo_recurso"):
            guia = st.text_input("Nombre del guía", placeholder="Nombre y apellidos")
            nombre = st.text_input("Nombre del recurso")
            municipio = st.text_input("Municipio")

            descripcion = st.text_area(
                "Información básica",
                placeholder="Indique web oficial, horarios, datos útiles o motivo por el que debería añadirse.",
            )

            enviar = st.form_submit_button("Enviar")

            if enviar:
                if not guia.strip():
                    st.warning("Indique su nombre.")
                    return

                if not nombre.strip():
                    st.warning("El nombre del recurso es obligatorio.")
                    return

                try:
                    save_incidencia({
                        "usuario_nombre": guia,
                        "tipo": "recurso",
                        "categoria": "nuevo",
                        "nombre": nombre,
                        "municipio": municipio,
                        "asunto": f"Nuevo recurso turístico: {nombre}",
                        "descripcion": descripcion,
                    })

                    st.success(
                        "Gracias. La propuesta ha sido registrada "
                        "y será revisada por APIT Cantabria."
                    )

                except Exception:
                    mensaje_error_envio()


def formulario_nuevo_restaurante():
    with st.expander("Proponer nuevo restaurante", expanded=False):
        with st.form("form_nuevo_restaurante"):
            guia = st.text_input("Nombre del guía", placeholder="Nombre y apellidos")
            nombre = st.text_input("Nombre del restaurante")
            municipio = st.text_input("Municipio")

            descripcion = st.text_area(
                "Información básica",
                placeholder="Indique si admite grupos, precio aproximado, experiencia con grupos o cualquier dato útil.",
            )

            enviar = st.form_submit_button("Enviar")

            if enviar:
                if not guia.strip():
                    st.warning("Indique su nombre.")
                    return

                if not nombre.strip():
                    st.warning("El nombre del restaurante es obligatorio.")
                    return

                try:
                    save_incidencia({
                        "usuario_nombre": guia,
                        "tipo": "restaurante",
                        "categoria": "nuevo",
                        "nombre": nombre,
                        "municipio": municipio,
                        "asunto": f"Nuevo restaurante: {nombre}",
                        "descripcion": descripcion,
                    })

                    st.success(
                        "Gracias. La propuesta ha sido registrada "
                        "y será revisada por APIT Cantabria."
                    )

                except Exception:
                    mensaje_error_envio()


def formulario_nueva_resena_restaurante(nombre, municipio=""):
    form_key = f"form_resena_{safe_key(nombre)}"

    with st.expander("Añadir reseña", expanded=False):
        with st.form(form_key):
            guia = st.text_input(
                "Nombre del guía",
                placeholder="Nombre y apellidos",
                key=f"guia_{form_key}",
            )

            fecha_visita = st.date_input(
                "Fecha",
                value=date.today(),
                format="DD/MM/YYYY",
                key=f"fecha_{form_key}",
            )

            n_personas = st.number_input(
                "Personas",
                min_value=1,
                step=1,
                key=f"personas_{form_key}",
            )

            precio = st.text_input(
                "Precio por persona",
                placeholder="Ejemplo: 22",
                key=f"precio_{form_key}",
            )

            valoracion = st.selectbox(
                "Valoración",
                [
                    "Seleccione...",
                    "⭐",
                    "⭐⭐",
                    "⭐⭐⭐",
                    "⭐⭐⭐⭐",
                    "⭐⭐⭐⭐⭐",
                ],
                key=f"rating_{form_key}",
            )

            comentario = st.text_area(
                "Comentario",
                placeholder="Breve valoración de la experiencia.",
                key=f"comentario_{form_key}",
            )

            enviar = st.form_submit_button("Guardar reseña")

            if enviar:
                if not guia.strip():
                    st.warning("Indique su nombre.")
                    return

                if valoracion == "Seleccione...":
                    st.warning("Seleccione una valoración.")
                    return

                if not comentario.strip():
                    st.warning("El comentario es obligatorio.")
                    return

                try:
                    save_resena_restaurante({
                        "restaurante": nombre,
                        "fecha": fecha_visita.strftime("%d/%m/%Y"),
                        "guia": guia,
                        "num_personas": int(n_personas),
                        "precio_por_persona": precio,
                        "rating": len(valoracion),
                        "comentario": comentario,
                    })

                    st.success("Gracias. La reseña ha sido registrada.")
                    st.cache_data.clear()

                except Exception:
                    mensaje_error_envio()


# ─────────────────────────────────────────────
# RECURSOS
# ─────────────────────────────────────────────

def modulo_recursos(dfs):
    recursos_df = dfs["recursos"]
    contenidos_df = dfs["contenidos_recursos"]

    hoy = date.today()
    fecha_max = date(hoy.year + 2, hoy.month, hoy.day)

    col_fecha, col_muni = st.columns([1, 1])

    with col_fecha:
        fecha_sel = st.date_input(
            "Consultar fecha",
            value=hoy,
            min_value=hoy,
            max_value=fecha_max,
            format="DD/MM/YYYY",
            key="rec_fecha",
        )

    with col_muni:
        municipios = ["Seleccione un municipio..."] + sorted(
            recursos_df["municipio"].dropna().unique()
        )
        muni = st.selectbox("Municipio", municipios, key="rec_muni")

    formulario_nuevo_recurso()

    if muni == "Seleccione un municipio...":
        st.info("Seleccione un municipio para consultar los recursos disponibles.")
        return

    df_fil = recursos_df.copy()

    if "activo" in df_fil.columns:
        df_fil = df_fil[df_fil["activo"] == True]

    df_fil = df_fil[df_fil["municipio"] == muni]

    if "prioridad" in df_fil.columns:
        df_fil = df_fil.sort_values(["prioridad", "recurso"])
    else:
        df_fil = df_fil.sort_values("recurso")

    if df_fil.empty:
        st.info("No hay recursos registrados para el municipio seleccionado.")
        return

    st.markdown(f"**{len(df_fil)} recurso(s) encontrado(s)**")

    for _, rec in df_fil.iterrows():
        nombre = limpiar(rec.get("recurso", ""))
        municipio = limpiar(rec.get("municipio", ""))
        tipo_rec = limpiar(rec.get("tipo", ""))
        web = limpiar(rec.get("web_oficial", ""))
        ultima_act = rec.get("ultima_actualizacion", None)

        contenido_fecha = filtrar_contenido(contenidos_df, nombre, fecha_sel)

        with st.container(border=True):
            st.markdown(f"### {nombre}")
            st.caption(f"{municipio} · {tipo_rec}")

            if contenido_fecha.empty or "bloque" not in contenido_fecha.columns:
                st.info("No hay información registrada para la fecha consultada.")
            else:
                for bloque_tipo, grupo in contenido_fecha.groupby("bloque"):
                    st.markdown(f"**{limpiar(bloque_tipo).upper()}**")

                    for _, fila in grupo.iterrows():
                        subtipo = limpiar(fila.get("subtipo", ""))
                        contenido = limpiar(fila.get("contenido", ""))
                        fuente = limpiar(fila.get("fuente", ""))

                        if subtipo:
                            st.markdown(f"**{subtipo}**")

                        if contenido:
                            st.write(contenido)

                        if fuente:
                            st.caption(f"Fuente: {fuente}")

                    st.divider()

            st.warning(
                "La información puede estar desactualizada. "
                "Contrástela con la fuente oficial antes de utilizarla."
            )

            if web:
                st.link_button("Web oficial", web)

            if pd.notna(ultima_act):
                try:
                    st.caption(
                        "Última actualización: "
                        + pd.to_datetime(ultima_act).strftime("%d/%m/%Y")
                    )
                except Exception:
                    pass

        formulario_incidencia(
            tipo="recurso",
            categoria="correccion",
            nombre=nombre,
            municipio=municipio,
        )


# ─────────────────────────────────────────────
# RESTAURANTES
# ─────────────────────────────────────────────

def modulo_restaurantes(dfs):
    rest_df = dfs["restaurantes"]
    exp_df = dfs["experiencias_restaurantes"].copy()

    if not exp_df.empty and "rating" in exp_df.columns:
        exp_df["rating"] = pd.to_numeric(exp_df["rating"], errors="coerce")

        rating_medio = (
            exp_df.dropna(subset=["rating"])
            .groupby("restaurante")["rating"]
            .agg(rating_medio="mean", n_resenas="count")
            .reset_index()
        )

        rest_df = rest_df.merge(rating_medio, on="restaurante", how="left")
    else:
        rest_df["rating_medio"] = None
        rest_df["n_resenas"] = 0

    municipios = ["Seleccione un municipio..."] + sorted(
        rest_df["municipio"].dropna().unique()
    )

    muni = st.selectbox("Municipio", municipios, key="rest_muni")

    formulario_nuevo_restaurante()

    if muni == "Seleccione un municipio...":
        st.info("Seleccione un municipio para consultar los restaurantes disponibles.")
        return

    df_fil = rest_df[rest_df["municipio"] == muni].copy()

    df_fil = df_fil.sort_values(
        "rating_medio",
        ascending=False,
        na_position="last",
    )

    if df_fil.empty:
        st.info("No hay restaurantes registrados para el municipio seleccionado.")
        return

    st.markdown(f"**{len(df_fil)} restaurante(s) encontrado(s)**")

    for _, row in df_fil.iterrows():
        nombre = limpiar(row.get("restaurante", ""))
        municipio = limpiar(row.get("municipio", ""))
        grupos = limpiar(row.get("admite_grupos", ""))
        precio = row.get("precio_menu_grupos", None)
        rating = row.get("rating_medio", None)
        n_res = int(row.get("n_resenas", 0)) if pd.notna(row.get("n_resenas")) else 0

        with st.container(border=True):
            st.markdown(f"### {nombre}")
            st.caption(municipio)

            etiquetas = []

            if grupos.upper() in ["SÍ", "SI", "YES"]:
                etiquetas.append("Admite grupos")

            if pd.notna(precio):
                etiquetas.append(f"Menú grupo: {precio} €/p.")

            if etiquetas:
                st.write(" · ".join(etiquetas))

            if pd.notna(rating):
                estrellas = int(round(rating))
                stars_str = "⭐" * estrellas + "☆" * (5 - estrellas)
                st.write(f"{stars_str} {rating:.1f}/5 ({n_res} reseña(s))")
            else:
                st.caption("Sin reseñas aún")

            resenas = exp_df[exp_df["restaurante"] == nombre].copy()

            if "fecha" in resenas.columns:
                resenas["fecha"] = pd.to_datetime(
                    resenas["fecha"],
                    dayfirst=True,
                    errors="coerce",
                )
                resenas = resenas.sort_values("fecha", ascending=False)

            if resenas.empty:
                st.caption("Sin reseñas registradas.")
            else:
                for _, res in resenas.head(3).iterrows():
                    fecha_str = (
                        pd.to_datetime(res["fecha"]).strftime("%d/%m/%Y")
                        if pd.notna(res.get("fecha"))
                        else ""
                    )

                    rating_res = pd.to_numeric(res.get("rating", 0), errors="coerce")
                    rating_res = int(rating_res) if pd.notna(rating_res) else 0
                    r_stars = "⭐" * rating_res

                    st.divider()
                    st.caption(
                        f"{r_stars} · {limpiar(res.get('guia', ''))} · "
                        f"{fecha_str} · {limpiar(res.get('num_personas', ''))} pax"
                    )
                    st.write(limpiar(res.get("comentario", "")))

        formulario_incidencia(
            tipo="restaurante",
            categoria="correccion",
            nombre=nombre,
            municipio=municipio,
        )

        formulario_nueva_resena_restaurante(
            nombre=nombre,
            municipio=municipio,
        )


# ─────────────────────────────────────────────
# APP PRINCIPAL
# ─────────────────────────────────────────────

def main():
    inject_css()
    cabecera()

    try:
        with st.spinner("Cargando información…"):
            dfs = load_data()

    except Exception:
        st.error(
            "No ha sido posible cargar la información. "
            "Inténtelo de nuevo más tarde o contacte con APIT Cantabria."
        )
        return

    col_ref, _ = st.columns([1, 3])

    with col_ref:
        if st.button("Actualizar datos"):
            st.cache_data.clear()
            st.rerun()

    st.divider()

    tab_rec, tab_rest = st.tabs(["Recursos", "Restaurantes"])

    with tab_rec:
        st.markdown(
            '<div class="section-header">Recursos turísticos</div>',
            unsafe_allow_html=True,
        )
        modulo_recursos(dfs)

    with tab_rest:
        st.markdown(
            '<div class="section-header">Restaurantes</div>',
            unsafe_allow_html=True,
        )
        modulo_restaurantes(dfs)

    st.markdown(
        """
        <div class="footer">
        APIT Cantabria<br>
        Asociación Profesional de Guías Oficiales de Turismo de Cantabria<br>
        Uso interno para profesionales.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
