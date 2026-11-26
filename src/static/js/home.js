const API = '/api/socios/';
const MONTO_CUOTA = Number($('config').dataset.montoCuota);

const estado = { pagina: 1, filtro: '', texto: '', total: 0, tamano: 20 };
let socioActual = null; // socio que se está editando / cobrando / borrando
let fichaId = null;     // socio cuya ficha está abierta (null = se ve el listado)
let pagoABorrar = null;

// ---------- Lista ----------
function insigniaEstado(s) {
    if (s.estado === 'inactivo') return '<span class="inline-block rounded-full bg-stone-200 px-3 py-1 text-sm font-bold text-stone-700">Inactivo</span>';
    if (s.estado === 'moroso') return '<span class="inline-block rounded-full bg-red-100 px-3 py-1 text-sm font-bold text-red-800">Debe cuota</span>';
    return '<span class="inline-block rounded-full bg-green-100 px-3 py-1 text-sm font-bold text-green-800">Al día ✓</span>';
}

function detalleEstado(s) {
    if (s.estado === 'inactivo') return '<p class="text-stone-600">Socio dado de baja (se conserva su historial)</p>';
    if (s.estado === 'moroso') return `<p class="text-red-800">Debe: ${esc(s.meses_adeudados.join(', '))}</p>`;
    return `<p class="text-stone-600">Próxima cuota: ${esc(s.proximo_mes_a_pagar)}</p>`;
}

function tarjetaSocio(s) {
    const debe = s.estado === 'moroso';
    const inactivo = s.estado === 'inactivo';
    const insignia = insigniaEstado(s);
    const detalle = detalleEstado(s);
    const ultimo = s.ultimo_pago
        ? `Último pago: ${fechaCorta(s.ultimo_pago)}`
        : 'Todavía no registra pagos';
    const whatsapp = debe && s.link_whatsapp
        ? `<a href="${esc(s.link_whatsapp)}" target="_blank" rel="noopener"
                class="rounded-lg bg-green-600 px-4 py-2 font-bold text-white hover:bg-green-700">Avisar por WhatsApp</a>`
        : '';
    return `
    <article class="rounded-xl bg-white p-4 shadow-sm ring-1 ${debe ? 'ring-red-200' : 'ring-stone-200'}">
        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div class="space-y-1">
                <div class="flex flex-wrap items-center gap-3">
                    <h3 class="text-xl font-bold"><a href="/socios/${s.id}/" data-ficha="${s.id}" class="hover:underline">${esc(s.apellido)}, ${esc(s.nombre)}</a></h3>
                    ${insignia}
                </div>
                <p class="text-stone-600">DNI ${esc(s.dni)} · WhatsApp ${esc(s.telefono)}</p>
                ${detalle}
                <p class="text-sm text-stone-500">${ultimo}</p>
            </div>
            <div class="flex flex-wrap gap-2" data-id="${s.id}">
                ${whatsapp}
                ${inactivo ? '' : '<button type="button" data-accion="pagar" class="rounded-lg border-2 border-green-600 px-4 py-2 font-bold text-green-700 hover:bg-green-50">Registrar pago</button>'}
                <button type="button" data-accion="ver" class="rounded-lg border border-stone-300 px-4 py-2 font-semibold hover:bg-stone-100">Ver ficha</button>
                <button type="button" data-accion="editar" class="rounded-lg border border-stone-300 px-4 py-2 font-semibold hover:bg-stone-100">Editar</button>
                <button type="button" data-accion="baja" class="rounded-lg border border-red-300 px-4 py-2 font-semibold text-red-700 hover:bg-red-50">Eliminar</button>
            </div>
        </div>
    </article>`;
}

let socios = [];

async function cargarLista() {
    const params = new URLSearchParams({ page: estado.pagina });
    if (estado.filtro) params.set('estado', estado.filtro);
    if (estado.texto) params.set('search', estado.texto);
    const lista = $('lista');
    // El Excel respeta el filtro y la búsqueda que se estén usando
    const paraExcel = new URLSearchParams();
    if (estado.filtro) paraExcel.set('estado', estado.filtro);
    if (estado.texto) paraExcel.set('search', estado.texto);
    $('btn-excel').href = `${API}exportar/` + (paraExcel.toString() ? `?${paraExcel}` : '');
    try {
        const datos = await pedir(`${API}?${params}`);
        socios = datos.results;
        estado.total = datos.count;
        lista.innerHTML = socios.length
            ? socios.map(tarjetaSocio).join('')
            : `<div class="rounded-xl bg-white p-8 text-center text-lg text-stone-600 ring-1 ring-stone-200">
                    ${estado.texto || estado.filtro ? 'No hay socios que coincidan con la búsqueda.' : 'Todavía no hay socios cargados. Usá el botón "+ Nuevo socio".'}
                </div>`;
        dibujarPaginacion();
    } catch (error) {
        // Si se borró el último socio de la última página, volver a la anterior
        if (error.estado === 404 && estado.pagina > 1) {
            estado.pagina -= 1;
            return cargarLista();
        }
        lista.innerHTML = `<div class="rounded-xl bg-red-50 p-6 text-red-800">${esc(mensajeDeError(error))}</div>`;
    }
}

function dibujarPaginacion() {
    const paginas = Math.max(1, Math.ceil(estado.total / estado.tamano));
    const nav = $('paginacion');
    if (paginas === 1) { nav.innerHTML = ''; return; }
    const estilo = 'rounded-lg border border-stone-300 bg-white px-4 py-2 font-semibold hover:bg-stone-100 disabled:opacity-40';
    nav.innerHTML = `
        <button type="button" id="pag-ant" class="${estilo}" ${estado.pagina <= 1 ? 'disabled' : ''}>← Anterior</button>
        <span>Página ${estado.pagina} de ${paginas}</span>
        <button type="button" id="pag-sig" class="${estilo}" ${estado.pagina >= paginas ? 'disabled' : ''}>Siguiente →</button>`;
    $('pag-ant').onclick = () => { estado.pagina -= 1; cargarLista(); };
    $('pag-sig').onclick = () => { estado.pagina += 1; cargarLista(); };
}

async function cargarResumen() {
    try {
        const r = await pedir(`${API}resumen/`);
        $('resumen-total').textContent = r.total;
        $('resumen-al-dia').textContent = r.al_dia;
        $('resumen-morosos').textContent = r.morosos;
    } catch (error) { /* la lista ya muestra el error */ }
}

function actualizarTodo() {
    if (fichaId) cargarFicha(fichaId);
    else cargarLista();
    cargarResumen();
}

function marcarPestana() {
    document.querySelectorAll('.pestana').forEach((b) => {
        const activa = b.dataset.filtro === estado.filtro;
        b.className = 'pestana rounded-full px-4 py-2 font-semibold ' +
            (activa ? 'bg-stone-900 text-white' : 'bg-white text-stone-700 ring-1 ring-stone-300 hover:bg-stone-200');
    });
}

function elegirFiltro(filtro) {
    estado.filtro = filtro;
    estado.pagina = 1;
    marcarPestana();
    cargarLista();
}

document.querySelectorAll('.pestana, .resumen').forEach((b) =>
    b.addEventListener('click', () => elegirFiltro(b.dataset.filtro)));

let temporizadorBusqueda;
$('buscador').addEventListener('input', (e) => {
    clearTimeout(temporizadorBusqueda);
    temporizadorBusqueda = setTimeout(() => {
        estado.texto = e.target.value.trim();
        estado.pagina = 1;
        cargarLista();
    }, 300);
});

// ---------- Acciones de cada tarjeta ----------
$('lista').addEventListener('click', (e) => {
    const boton = e.target.closest('button[data-accion]');
    if (!boton) return;
    const id = Number(boton.parentElement.dataset.id);
    socioActual = socios.find((s) => s.id === id);
    if (!socioActual) return;
    if (boton.dataset.accion === 'ver') irAFicha(socioActual.id);
    if (boton.dataset.accion === 'editar') abrirFormulario(socioActual);
    if (boton.dataset.accion === 'pagar') abrirPago(socioActual);
    if (boton.dataset.accion === 'baja') abrirBaja(socioActual);
});

$('lista').addEventListener('click', (e) => {
    const enlace = e.target.closest('a[data-ficha]');
    if (!enlace) return;
    e.preventDefault();
    irAFicha(Number(enlace.dataset.ficha));
});

document.querySelectorAll('[data-cerrar]').forEach((b) =>
    b.addEventListener('click', () => b.closest('dialog').close()));

// ---------- Alta y edición ----------
const formSocio = $('form-socio');

function limpiarErrores() {
    $('error-general').classList.add('hidden');
    formSocio.querySelectorAll('.error-campo').forEach((s) => { s.textContent = ''; });
    formSocio.querySelectorAll('.campo').forEach((c) => c.classList.remove('border-red-500'));
}

function abrirFormulario(socio = null) {
    limpiarErrores();
    formSocio.reset();
    $('titulo-socio').textContent = socio ? 'Editar socio' : 'Nuevo socio';
    for (const nombre of ['nombre', 'apellido', 'dni', 'telefono', 'email', 'direccion', 'fecha_alta']) {
        formSocio.elements[nombre].value = socio ? (socio[nombre] ?? '') : (nombre === 'fecha_alta' ? hoyIso() : '');
    }
    formSocio.elements.activo.checked = socio ? socio.activo : true;
    if (!socio) socioActual = null;
    $('dlg-socio').showModal();
}

$('btn-nuevo').addEventListener('click', () => abrirFormulario());

formSocio.addEventListener('submit', async (e) => {
    e.preventDefault();
    limpiarErrores();
    const cuerpo = {};
    for (const nombre of ['nombre', 'apellido', 'dni', 'telefono', 'email', 'direccion', 'fecha_alta']) {
        const valor = formSocio.elements[nombre].value.trim();
        cuerpo[nombre] = (valor === '' && ['email', 'direccion'].includes(nombre)) ? null : valor;
    }
    cuerpo.activo = formSocio.elements.activo.checked;
    const boton = $('btn-guardar');
    boton.disabled = true;
    try {
        if (socioActual) {
            await pedir(`${API}${socioActual.id}/`, { method: 'PUT', body: JSON.stringify(cuerpo) });
        } else {
            await pedir(API, { method: 'POST', body: JSON.stringify(cuerpo) });
        }
        $('dlg-socio').close();
        avisar(socioActual ? 'Datos del socio guardados.' : 'Socio agregado.');
        actualizarTodo();
    } catch (error) {
        let hayErroresDeCampo = false;
        if (error.datos && typeof error.datos === 'object') {
            for (const [campo, mensajes] of Object.entries(error.datos)) {
                const input = formSocio.elements[campo];
                if (input && Array.isArray(mensajes)) {
                    input.classList.add('border-red-500');
                    input.parentElement.querySelector('.error-campo').textContent = mensajes.join(' ');
                    hayErroresDeCampo = true;
                }
            }
        }
        if (!hayErroresDeCampo) {
            const general = $('error-general');
            general.textContent = mensajeDeError(error);
            general.classList.remove('hidden');
        }
    } finally {
        boton.disabled = false;
    }
});

// ---------- Registrar pago ----------
$('mes-pago').innerHTML = MESES.map((m, i) => `<option value="${i + 1}">${m}</option>`).join('');

function abrirPago(socio) {
    $('error-pago').classList.add('hidden');
    $('texto-pago').innerHTML =
        `Pago de <strong>${esc(socio.nombre)} ${esc(socio.apellido)}</strong>. Se sugiere la cuota de ${esc(socio.proximo_mes_a_pagar)}.`;
    $('mes-pago').value = socio.proximo_periodo.mes;
    $('anio-pago').value = socio.proximo_periodo.anio;
    $('fecha-pago').value = hoyIso();
    $('forma-pago').value = 'efectivo';
    $('monto-pago').value = MONTO_CUOTA;
    $('dlg-pago').showModal();
}

$('form-pago').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const cuerpo = {
            mes: Number($('mes-pago').value),
            anio: Number($('anio-pago').value),
            fecha_pago: $('fecha-pago').value,
            forma_pago: $('forma-pago').value,
            monto: $('monto-pago').value,
        };
        await pedir(`${API}${socioActual.id}/pagar/`, { method: 'POST', body: JSON.stringify(cuerpo) });
        $('dlg-pago').close();
        avisar(`Pago registrado: ${MESES[cuerpo.mes - 1]} ${cuerpo.anio}, ${plata(cuerpo.monto)}.`);
        actualizarTodo();
    } catch (error) {
        const caja = $('error-pago');
        caja.textContent = mensajeDeError(error);
        caja.classList.remove('hidden');
    }
});

// ---------- Dar de baja ----------
function abrirBaja(socio) {
    $('texto-baja').innerHTML =
        `¿Seguro que querés dar de baja a <strong>${esc(socio.nombre)} ${esc(socio.apellido)}</strong> (DNI ${esc(socio.dni)})?`;
    $('dlg-baja').showModal();
}

$('form-baja').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        await pedir(`${API}${socioActual.id}/`, { method: 'DELETE' });
        $('dlg-baja').close();
        avisar('Socio eliminado.');
        if (fichaId) irAlListado(); else actualizarTodo();
    } catch (error) {
        $('dlg-baja').close();
        avisar(mensajeDeError(error));
    }
});

// ---------- Ficha del socio ----------
async function cargarFicha(id) {
    try {
        const s = await pedir(`${API}${id}/`);
        if (fichaId !== id) return;
        socioActual = s;
        dibujarFicha(s);
    } catch (error) {
        $('ficha-datos').innerHTML = `<div class="rounded-xl bg-red-50 p-6 text-red-800">${error.estado === 404 ? 'No se encontró ese socio.' : esc(mensajeDeError(error))}</div>`;
        $('ficha-pagos').innerHTML = '';
    }
}

function dato(titulo, valor) {
    return `<div><p class="text-sm text-stone-500">${titulo}</p><p class="text-lg font-bold">${esc(valor) || '–'}</p></div>`;
}

function dibujarFicha(s) {
    document.title = `${s.apellido}, ${s.nombre} · La Lonja`;
    const activo = s.estado !== 'inactivo';
    const whatsapp = s.estado === 'moroso' && s.link_whatsapp
        ? `<a href="${esc(s.link_whatsapp)}" target="_blank" rel="noopener" class="rounded-lg bg-green-600 px-4 py-2 font-bold text-white hover:bg-green-700">Avisar por WhatsApp</a>` : '';
    $('ficha-datos').innerHTML = `
    <section class="rounded-xl bg-white p-6 shadow-sm ring-1 ring-stone-200">
        <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div class="space-y-2">
                <h2 class="text-3xl font-extrabold">${esc(s.nombre)} ${esc(s.apellido)}</h2>
                ${insigniaEstado(s)}
                ${detalleEstado(s)}
            </div>
            <div class="flex flex-wrap gap-2">
                ${whatsapp}
                ${activo ? '<button type="button" id="ficha-pagar" class="rounded-lg bg-green-600 px-5 py-3 font-bold text-white hover:bg-green-700">Cobrar cuota</button>' : ''}
                <button type="button" id="ficha-editar" class="rounded-lg border border-stone-300 px-5 py-3 font-semibold hover:bg-stone-100">Editar</button>
                <button type="button" id="ficha-eliminar" class="rounded-lg border border-red-300 px-5 py-3 font-semibold text-red-700 hover:bg-red-50">Eliminar</button>
            </div>
        </div>
        <div class="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            ${dato('DNI', s.dni)}
            ${dato('WhatsApp', s.telefono)}
            ${dato('Email', s.email)}
            ${dato('Dirección', s.direccion)}
            ${dato('Socio desde', fechaCorta(s.fecha_alta))}
        </div>
    </section>`;
    if ($('ficha-pagar')) $('ficha-pagar').onclick = () => abrirPago(s);
    $('ficha-editar').onclick = () => abrirFormulario(s);
    $('ficha-eliminar').onclick = () => abrirBaja(s);

    $('ficha-pagos').innerHTML = s.pagos.length ? `
        <table class="w-full min-w-[34rem] text-left">
            <thead class="text-sm uppercase tracking-wide text-stone-500">
                <tr><th class="py-2 pr-4">Cuota de</th><th class="py-2 pr-4">Monto</th><th class="py-2 pr-4">Pagó el</th><th class="py-2 pr-4">Forma</th><th></th></tr>
            </thead>
            <tbody>${s.pagos.map((p) => `
                <tr class="border-t border-stone-200">
                    <td class="py-3 pr-4 font-bold">${esc(p.mes_nombre)} ${p.anio}</td>
                    <td class="py-3 pr-4">${plata(Number(p.monto))}</td>
                    <td class="py-3 pr-4">${fechaCorta(p.fecha_pago)}</td>
                    <td class="py-3 pr-4">${esc(p.forma_pago_nombre)}</td>
                    <td class="py-3 text-right"><button type="button" data-pago="${p.id}" class="font-semibold text-red-700 hover:underline">Eliminar</button></td>
                </tr>`).join('')}
            </tbody>
        </table>` : '<p class="py-4 text-stone-600">Todavía no registra pagos.</p>';
}

$('ficha-pagos').addEventListener('click', (e) => {
    const boton = e.target.closest('button[data-pago]');
    if (!boton) return;
    pagoABorrar = socioActual.pagos.find((p) => p.id === Number(boton.dataset.pago));
    $('texto-borrar-pago').innerHTML = `¿Eliminar el pago de <strong>${esc(pagoABorrar.mes_nombre)} ${pagoABorrar.anio}</strong> (${plata(Number(pagoABorrar.monto))})?`;
    $('dlg-borrar-pago').showModal();
});

$('form-borrar-pago').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        await pedir(`/api/pagos/${pagoABorrar.id}/`, { method: 'DELETE' });
        $('dlg-borrar-pago').close();
        avisar('Pago eliminado.');
        actualizarTodo();
    } catch (error) {
        $('dlg-borrar-pago').close();
        avisar(mensajeDeError(error));
    }
});

// ---------- Navegación entre listado y ficha (sin recargar la página) ----------
function mostrarVista() {
    const coincidencia = location.pathname.match(/^\/socios\/(\d+)\/$/);
    fichaId = coincidencia ? Number(coincidencia[1]) : null;
    $('vista-lista').classList.toggle('hidden', fichaId !== null);
    $('vista-ficha').classList.toggle('hidden', fichaId === null);
    if (fichaId !== null) {
        $('ficha-datos').innerHTML = '<p class="text-stone-600">Cargando...</p>';
        $('ficha-pagos').innerHTML = '';
        cargarFicha(fichaId);
    } else {
        document.title = 'La Lonja - Secretaría';
        cargarLista();
    }
    cargarResumen();
}

function irAFicha(id) { history.pushState({}, '', `/socios/${id}/`); window.scrollTo(0, 0); mostrarVista(); }
function irAlListado() { history.pushState({}, '', '/'); mostrarVista(); }

$('btn-volver').addEventListener('click', (e) => { e.preventDefault(); irAlListado(); });
window.addEventListener('popstate', mostrarVista);

marcarPestana();
mostrarVista();