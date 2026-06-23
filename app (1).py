"""
CMS Turístico de Cantabria
Recursos y Restaurantes
Formularios internos + Google Apps Script + Google Sheets
"""

import streamlit as st
import pandas as pd
from datetime import date
import textwrap
import requests
import re
import html as html_lib


st.set_page_config(
    page_title="CMS Cantabria",
    page_icon="🏔️",
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


# ─────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────

def html(s: str) -> str:
    return textwrap.dedent(s).strip()


def esc(value) -> str:
    if pd.isna(value):
        return ""
    return html_lib.escape(str(value))


def safe_key(texto: str) -> str:
    texto = str(texto).lower().strip()
    texto = re.sub(r"[^a-z0-9áéíóúñü]+", "_", texto)
    return texto.strip("_")


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
# CARGA DE DATOS
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
# ESTILOS
# ─────────────────────────────────────────────

def inject_css():
    st.markdown(html("""
    <style>
    .block-container {
        max-width: 720px;
        padding: 1rem 1rem 4rem;
    }

    .section-header {
        background: linear-gradient(135deg, #1a4a6b 0%, #0d7c9e 100%);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        font-weight: 600;
    }

    .card {
        background: #ffffff;
        border: 1px solid #e5e9ef;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }

    .card-title {
        font-weight: 700;
        font-size: 1rem;
        color: #1a2e40;
        margin-bottom: 0.4rem;
    }

    .badge {
        display: inline-block;
        background: #e0f2fe;
        color: #0369a1;
        border-radius: 20px;
        padding: 0.15rem 0.65rem;
        font-size: 0.72rem;
        font-weight: 600;
        margin-right: 0.3rem;
        margin-bottom: 0.2rem;
    }

    .badge-green {
        background: #dcfce7;
        color: #15803d;
    }

    .badge-amber {
        background: #fef9c3;
        color: #92400e;
    }

    .bloque {
        background: #f4f8fc;
        border-left: 3px solid #0d7c9e;
        border-radius: 0 8px 8px 0;
        padding: 0.55rem 0.8rem;
        margin-bottom: 0.45rem;
    }

    .bloque-label {
        font-size: 0.7rem;
        font-weight: 600;
        color: #0d7c9e;
        text-transform: uppercase;
    }

    .bloque-subtipo {
        font-weight: 600;
        color: #1a2e40;
        font-size: 0.87rem;
    }

    .bloque-contenido {
        color: #374151;
        font-size: 0.87rem;
    }

    .disclaimer {
        background: #fffbeb;
        border: 1px solid #fcd34d;
        border-radius: 8px;
        padding: 0.55rem 0.8rem;
        margin-top: 0.6rem;
        font-size: 0.78rem;
        color: #78350f;
    }

    .no-results {
        text-align: center;
        color: #6b7280;
        padding: 1.5rem 1rem;
        font-size: 0.9rem;
    }
    </style>
    """), unsafe_allow_html=True)


# ─────────────────────────────────────────────
# BLOQUES VISUALES
# ─────────────────────────────────────────────

def build_bloque(bloque_tipo, subtipo, contenido, fuente):
    fuente_html = (
        f'<br><small style="color:#9ca3af">Fuente: {esc(fuente)}</small>'
        if fuente else ""
    )

    return (
        '<div class="bloque">'
        f'<div class="bloque-label">{esc(bloque_tipo)}</div>'
        f'<div class="bloque-subtipo">{esc(subtipo)}</div>'
        f'<div class="bloque-contenido">{esc(contenido)}{fuente_html}</div>'
        '</div>'
    )


def build_disclaimer(web, ultima_act):
    web_link = ""

    if web and pd.notna(web):
        web_link = f' · <a href="{esc(web)}" target="_blank">Web oficial</a>'

    if pd.notna(ultima_act) and ultima_act:
        try:
            fecha_act = pd.to_datetime(ultima_act).strftime("%d/%m/%Y")
            act_str = f" · Última actualización: <strong>{fecha_act}</strong>"
        except Exception:
            act_str = ""
    else:
        act_str = ""

    return (
        '<div class="disclaimer">'
        '<strong>Aviso:</strong> La información puede estar desactualizada. '
        'Contrástela con la fuente oficial antes de utilizarla.'
        f'{web_link}{act_str}'
        '</div>'
    )


def build_resena(r_stars, guia, fecha_str, n_p, comentario):
    return (
        '<div style="border-top:1px solid #e5e9ef;'
        'padding-top:0.5rem;margin-top:0.5rem;">'
        f'<div style="font-size:0.78rem;color:#6b7a8d;">'
        f'{esc(r_stars)} · {esc(guia)} · {esc(fecha_str)} · {esc(n_p)} pax'
        '</div>'
        f'<div style="font-size:0.85rem;color:#374151;margin-top:0.2rem;">'
        f'{esc(comentario)}'
        '</div>'
        '</div>'
    )


# ─────────────────────────────────────────────
# FORMULARIOS
# ─────────────────────────────────────────────

def mensaje_error_envio():
    st.error(
        "No ha sido posible enviar la información. "
        "Inténtelo de nuevo más tarde o contacte con APIT Cantabria."
    )


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

                    st.success("Gracias. La información ha sido registrada y será revisada por APIT Cantabria.")

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
                placeholder="Indique web oficial, horarios, datos útiles o motivo por el que debería añadirse."
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

                    st.success("Gracias. La propuesta ha sido registrada y será revisada por APIT Cantabria.")

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
                placeholder="Indique si admite grupos, precio aproximado, experiencia con grupos o cualquier dato útil."
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

                    st.success("Gracias. La propuesta ha sido registrada y será revisada por APIT Cantabria.")

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
# MÓDULO RECURSOS
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
        st.markdown(
            '<div class="no-results">Seleccione un municipio para consultar los recursos disponibles.</div>',
            unsafe_allow_html=True,
        )
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
        st.markdown(
            '<div class="no-results">No hay recursos registrados para el municipio seleccionado.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(f"**{len(df_fil)} recurso(s) encontrado(s)**")

    for _, rec in df_fil.iterrows():
        nombre = rec["recurso"]
        municipio = rec.get("municipio", "")
        tipo_rec = rec.get("tipo", "")
        web = rec.get("web_oficial", "")
        ultima_act = rec.get("ultima_actualizacion", None)

        contenido_fecha = filtrar_contenido(contenidos_df, nombre, fecha_sel)

        if not contenido_fecha.empty and "bloque" in contenido_fecha.columns:
            bloques_html = ""

            for bloque_tipo, grupo in contenido_fecha.groupby("bloque"):
                for _, fila in grupo.iterrows():
                    bloques_html += build_bloque(
                        bloque_tipo,
                        fila.get("subtipo", "") or "",
                        fila.get("contenido", "") or "",
                        fila.get("fuente", "") or "",
                    )
        else:
            bloques_html = (
                '<small style="color:#6b7280">'
                'No hay información registrada para la fecha consultada.'
                '</small>'
            )

        st.markdown(f"""
        <div class="card">
            <div class="card-title">🏛️ {esc(nombre)}</div>
            <div>
                <span class="badge">{esc(municipio)}</span>
                <span class="badge badge-amber">{esc(tipo_rec)}</span>
            </div>
            {bloques_html}
            {build_disclaimer(web, ultima_act)}
        </div>
        """, unsafe_allow_html=True)

        formulario_incidencia(
            tipo="recurso",
            categoria="correccion",
            nombre=nombre,
            municipio=municipio,
        )


# ─────────────────────────────────────────────
# MÓDULO RESTAURANTES
# ─────────────────────────────────────────────

def modulo_restaurantes(dfs):
    rest_df = dfs["restaurantes"]
    exp_df = dfs["experiencias_restaurantes"]

    if not exp_df.empty and "rating" in exp_df.columns:
        rating_medio = (
            exp_df.groupby("restaurante")["rating"]
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
        nombre = row["restaurante"]
        municipio = row.get("municipio", "")
        grupos = row.get("admite_grupos", "")
        precio = row.get("precio_menu_grupos", None)
        rating = row.get("rating_medio", None)
        n_res = int(row.get("n_resenas", 0)) if pd.notna(row.get("n_resenas")) else 0

        with st.container(border=True):
            st.markdown(f"**{nombre}**")
            st.caption(municipio)

            etiquetas = []

            if str(grupos).upper() in ["SÍ", "SI", "YES"]:
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
                resenas["fecha"] = pd.to_datetime(resenas["fecha"], errors="coerce")
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

                    r_stars = "⭐" * int(res.get("rating", 0))

                    st.markdown("---")
                    st.caption(
                        f"{r_stars} · {res.get('guia', '')} · "
                        f"{fecha_str} · {res.get('num_personas', '')} pax"
                    )
                    st.write(res.get("comentario", ""))

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

    st.markdown(html("""
    <div style="text-align:center;padding:1.2rem 0 0.5rem;">
        <div style="font-size:2rem;">🏔️</div>
        <div style="font-weight:700;font-size:1.35rem;color:#1a2e40;">
            CMS Cantabria
        </div>
        <div style="color:#6b7a8d;font-size:0.82rem;margin-top:0.2rem;">
            Panel de Guías Turísticos
        </div>
    </div>
    """), unsafe_allow_html=True)

    try:
        with st.spinner("Cargando datos…"):
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
            '<div class="section-header">Recursos Turísticos</div>',
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
        '<div style="text-align:center;color:#9ca3af;'
        'font-size:0.72rem;margin-top:2rem;padding-bottom:1rem;">'
        'CMS Cantabria · Información para uso profesional interno'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
