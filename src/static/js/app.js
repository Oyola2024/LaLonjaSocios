const CSRF = document.querySelector('meta[name="csrf-token"]').content;
const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

const $ = (id) => document.getElementById(id);
const esc = (valor) => String(valor ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fechaCorta = (iso) => iso ? iso.split('-').reverse().join('/') : '';
const hoyIso = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
const plata = (n) => new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(n);

// ---------- Comunicación con la API ----------
async function pedir(url, opciones = {}) {
    const respuesta = await fetch(url, {
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        ...opciones,
    });
    if (respuesta.status === 204) return null;
    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw { estado: respuesta.status, datos };
    return datos;
}

function mensajeDeError(error) {
    if (error.estado === 401 || error.estado === 403) {
        return 'Se venció la sesión. Recargá la página e ingresá de nuevo.';
    }
    if (error.datos && error.datos.detail) return error.datos.detail;
    if (error.datos && typeof error.datos === 'object') {
        const primero = Object.values(error.datos).find((v) => Array.isArray(v));
        if (primero) return primero.join(' ');
    }
    if (error.datos && error.datos.non_field_errors) return error.datos.non_field_errors.join(' ');
    return 'No se pudo completar la acción. Probá de nuevo.';
}

let temporizadorAviso;
function avisar(texto) {
    const aviso = $('aviso');
    aviso.textContent = texto;
    aviso.classList.remove('hidden');
    clearTimeout(temporizadorAviso);
    temporizadorAviso = setTimeout(() => aviso.classList.add('hidden'), 3500);
}