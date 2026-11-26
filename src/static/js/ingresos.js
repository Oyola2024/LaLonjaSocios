const URL_INGRESOS = '/api/pagos/ingresos/';
const monto = (n) => Number(n) > 0 ? plata(Number(n)) : '–';

async function cargarIngresos(anio) {
try {
    const d = await pedir(URL_INGRESOS + (anio ? `?anio=${anio}` : ''));
    $('anio').innerHTML = d.anios.map((a) => `<option value="${a}">${a}</option>`).join('');
    $('anio').value = d.anio;

    $('total-anio').textContent = plata(Number(d.total));
    $('cobros-anio').textContent = `${d.cantidad} ${d.cantidad === 1 ? 'cobro' : 'cobros'}`;
    $('total-efectivo').textContent = plata(Number(d.efectivo));
    $('total-transferencia').textContent = plata(Number(d.transferencia));

    const mayor = Math.max(...d.meses.map((m) => Number(m.total)));
    const mejor = d.meses.find((m) => Number(m.total) === mayor);
    $('mejor-mes').textContent = mayor > 0 ? mejor.mes_nombre : '–';
    $('mejor-mes-total').textContent = mayor > 0 ? plata(mayor) : 'Todavía no hay cobros';

    const hoy = new Date();
    $('tabla').innerHTML = `
    <table class="w-full min-w-[36rem] text-left">
        <thead class="text-sm uppercase tracking-wide text-stone-500">
            <tr><th class="py-2 pr-4">Mes</th><th class="py-2 pr-4">Cobros</th><th class="py-2 pr-4">Efectivo</th><th class="py-2 pr-4">Transferencia</th><th class="py-2 text-right">Total</th></tr>
        </thead>
        <tbody>${d.meses.map((m) => {
            const actual = d.anio === hoy.getFullYear() && m.mes === hoy.getMonth() + 1;
            const ancho = mayor > 0 ? Math.round(Number(m.total) / mayor * 100) : 0;
            return `
            <tr class="border-t border-stone-200 ${actual ? 'bg-amber-50' : ''}">
                <td class="py-3 pr-4">
                    <span class="font-bold">${esc(m.mes_nombre)}</span>${actual ? ' <span class="text-sm text-amber-700">(este mes)</span>' : ''}
                    <div class="mt-1 h-2 rounded-full bg-red-600" style="width: ${ancho}%"></div>
                </td>
                <td class="py-3 pr-4">${m.cantidad || '–'}</td>
                <td class="py-3 pr-4">${monto(m.efectivo)}</td>
                <td class="py-3 pr-4">${monto(m.transferencia)}</td>
                <td class="py-3 text-right font-bold">${monto(m.total)}</td>
            </tr>`;
        }).join('')}
        </tbody>
        <tfoot>
            <tr class="border-t-2 border-stone-300 font-extrabold">
                <td class="py-3 pr-4">Total ${d.anio}</td>
                <td class="py-3 pr-4">${d.cantidad}</td>
                <td class="py-3 pr-4">${plata(Number(d.efectivo))}</td>
                <td class="py-3 pr-4">${plata(Number(d.transferencia))}</td>
                <td class="py-3 text-right">${plata(Number(d.total))}</td>
            </tr>
        </tfoot>
    </table>`;
} catch (error) {
    $('tabla').innerHTML = `<p class="text-red-800">${esc(mensajeDeError(error))}</p>`;
}
}

$('anio').addEventListener('change', (e) => cargarIngresos(e.target.value));
cargarIngresos();