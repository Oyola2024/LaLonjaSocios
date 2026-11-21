from datetime import date
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Socio, Pago


def con_fecha(anio, mes, dia):
    """Simula que hoy es otro día (la regla del día 3 depende de la fecha)."""
    return patch('socios.models.hoy', return_value=date(anio, mes, dia))


def crear_socio(**datos):
    valores = {
        'nombre': 'Juan',
        'apellido': 'Pérez',
        'dni': '30111222',
        'telefono': '3584123456',
        'fecha_alta': date(2026, 9, 10),
    }
    valores.update(datos)
    return Socio.objects.create(**valores)


def pagar(socio, anio, mes):
    return Pago.objects.create(socio=socio, anio=anio, mes=mes, monto=5000)


class EstadoDeCuotaTests(TestCase):
    def test_sin_pagos_debe_todos_los_meses_vencidos(self):
        socio = crear_socio()  # alta en septiembre
        with con_fecha(2026, 11, 19):
            self.assertEqual(socio.meses_adeudados(), [(2026, 9), (2026, 10), (2026, 11)])
            self.assertFalse(socio.al_dia)

    def test_pagando_los_meses_queda_al_dia(self):
        socio = crear_socio()
        for mes in (9, 10, 11):
            pagar(socio, 2026, mes)
        with con_fecha(2026, 11, 19):
            self.assertTrue(socio.al_dia)

    def test_debe_solo_el_mes_sin_pago(self):
        socio = crear_socio()
        pagar(socio, 2026, 9)
        pagar(socio, 2026, 10)
        with con_fecha(2026, 11, 19):
            self.assertEqual(socio.meses_adeudados(), [(2026, 11)])

    def test_hasta_el_dia_3_inclusive_el_mes_actual_no_esta_vencido(self):
        socio = crear_socio()
        pagar(socio, 2026, 9)
        pagar(socio, 2026, 10)
        with con_fecha(2026, 11, 3):
            self.assertTrue(socio.al_dia)
        with con_fecha(2026, 11, 4):
            self.assertFalse(socio.al_dia)

    def test_cambio_de_anio(self):
        socio = crear_socio(fecha_alta=date(2026, 11, 1))
        pagar(socio, 2026, 11)
        with con_fecha(2027, 1, 2):
            self.assertEqual(socio.meses_adeudados(), [(2026, 12)])
        with con_fecha(2027, 1, 10):
            self.assertEqual(socio.meses_adeudados(), [(2026, 12), (2027, 1)])

    def test_socio_nuevo_del_mes_vigente_recien_vence_despues_del_3(self):
        socio = crear_socio(fecha_alta=date(2026, 11, 2))
        with con_fecha(2026, 11, 3):
            self.assertTrue(socio.al_dia)

    def test_proximo_mes_a_pagar(self):
        socio = crear_socio()
        with con_fecha(2026, 11, 19):
            self.assertEqual(socio.proximo_mes_a_pagar(), (2026, 9))
            for mes in (9, 10, 11):
                pagar(socio, 2026, mes)
            # al día: lo siguiente es la cuota que viene
            self.assertEqual(socio.proximo_mes_a_pagar(), (2026, 12))

    def test_ultimo_pago(self):
        socio = crear_socio()
        self.assertIsNone(socio.ultimo_pago())
        pagar(socio, 2026, 10)
        pagar(socio, 2026, 9)
        self.assertEqual(socio.ultimo_pago().mes, 10)


class WhatsAppTests(TestCase):
    def test_normaliza_el_telefono(self):
        casos = {
            '3584123456': '5493584123456',
            '03584123456': '5493584123456',
            '+54 9 358 412-3456': '5493584123456',
            '543584123456': '5493584123456',
        }
        for escrito, esperado in casos.items():
            self.assertEqual(crear_socio(dni='1', telefono=escrito).telefono_whatsapp(), esperado)
            Socio.objects.all().delete()

    def test_al_dia_no_tiene_link(self):
        socio = crear_socio()
        for mes in (9, 10, 11):
            pagar(socio, 2026, mes)
        with con_fecha(2026, 11, 19):
            self.assertIsNone(socio.link_whatsapp())

    def test_moroso_tiene_link_con_mensaje(self):
        socio = crear_socio()
        pagar(socio, 2026, 9)
        with con_fecha(2026, 11, 19):
            link = socio.link_whatsapp()
        url = urlparse(link)
        self.assertEqual(url.netloc, 'wa.me')
        self.assertEqual(url.path, '/5493584123456')
        mensaje = parse_qs(url.query)['text'][0]
        self.assertIn('Hola Juan', mensaje)
        self.assertIn('Octubre 2026 y Noviembre 2026', mensaje)


class SocioApiTests(APITestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('secretaria', password='clave12345', is_staff=True)
        self.client.force_authenticate(self.usuario)
        self.datos = {
            'nombre': 'Ana',
            'apellido': 'Gómez',
            'dni': '28555666',
            'telefono': '358 412-3456',
            'fecha_alta': '2026-11-01',
        }

    def test_requiere_login(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/socios/').status_code, (401, 403))

    def test_alta_de_socio_limpia_el_telefono(self):
        respuesta = self.client.post('/api/socios/', self.datos, format='json')
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(Socio.objects.get().telefono, '3584123456')

    def test_dni_invalido_y_repetido(self):
        malo = self.client.post('/api/socios/', {**self.datos, 'dni': '12.345.678'}, format='json')
        self.assertEqual(malo.status_code, 400)
        self.assertIn('dni', malo.data)
        self.client.post('/api/socios/', self.datos, format='json')
        repetido = self.client.post('/api/socios/', self.datos, format='json')
        self.assertEqual(repetido.status_code, 400)
        self.assertIn('dni', repetido.data)
        self.assertEqual(repetido.data['dni'][0], 'Ya hay un socio registrado con ese DNI.')

    def test_telefono_invalido(self):
        respuesta = self.client.post('/api/socios/', {**self.datos, 'telefono': '12'}, format='json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('telefono', respuesta.data)

    def test_editar_socio(self):
        socio = crear_socio()
        respuesta = self.client.put(
            f'/api/socios/{socio.id}/', {**self.datos, 'dni': socio.dni}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        socio.refresh_from_db()
        self.assertEqual(socio.nombre, 'Ana')

    def test_dar_de_baja_borra_tambien_los_pagos(self):
        socio = crear_socio()
        pagar(socio, 2026, 9)
        respuesta = self.client.delete(f'/api/socios/{socio.id}/')
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(Socio.objects.count(), 0)
        self.assertEqual(Pago.objects.count(), 0)

    def test_listado_incluye_estado_y_link(self):
        crear_socio()
        with con_fecha(2026, 11, 19):
            respuesta = self.client.get('/api/socios/')
        socio = respuesta.data['results'][0]
        self.assertEqual(socio['estado'], 'moroso')
        self.assertEqual(socio['meses_adeudados'], ['Septiembre 2026', 'Octubre 2026', 'Noviembre 2026'])
        self.assertTrue(socio['link_whatsapp'].startswith('https://wa.me/549'))

    def test_filtro_por_estado_y_busqueda(self):
        debe = crear_socio()
        al_dia = crear_socio(nombre='María', apellido='López', dni='20999888')
        for mes in (9, 10, 11):
            pagar(al_dia, 2026, mes)
        with con_fecha(2026, 11, 19):
            morosos = self.client.get('/api/socios/?estado=moroso')
            sanos = self.client.get('/api/socios/?estado=al_dia')
            buscados = self.client.get('/api/socios/?search=20999888')
        self.assertEqual([s['id'] for s in morosos.data['results']], [debe.id])
        self.assertEqual([s['id'] for s in sanos.data['results']], [al_dia.id])
        self.assertEqual([s['id'] for s in buscados.data['results']], [al_dia.id])

    def test_resumen(self):
        crear_socio()
        al_dia = crear_socio(dni='20999888')
        for mes in (9, 10, 11):
            pagar(al_dia, 2026, mes)
        with con_fecha(2026, 11, 19):
            respuesta = self.client.get('/api/socios/resumen/')
        self.assertEqual(respuesta.data, {'total': 2, 'al_dia': 1, 'morosos': 1, 'inactivos': 0})

    def test_pagar_registra_la_cuota_mas_vieja(self):
        socio = crear_socio()
        with con_fecha(2026, 11, 19):
            respuesta = self.client.post(f'/api/socios/{socio.id}/pagar/', {}, format='json')
        self.assertEqual(respuesta.status_code, 201)
        pago = Pago.objects.get()
        self.assertEqual((pago.anio, pago.mes), (2026, 9))
        self.assertEqual(pago.monto, 5000)
        self.assertEqual(respuesta.data['meses_adeudados'], ['Octubre 2026', 'Noviembre 2026'])

    def test_pagar_hasta_quedar_al_dia(self):
        socio = crear_socio()
        with con_fecha(2026, 11, 19):
            for _ in range(3):
                respuesta = self.client.post(f'/api/socios/{socio.id}/pagar/', {'monto': '6000'}, format='json')
        self.assertEqual(respuesta.data['estado'], 'al_dia')
        self.assertEqual(respuesta.data['link_whatsapp'], None)
        self.assertEqual(Pago.objects.filter(monto=6000).count(), 3)

    def test_pagar_mes_ya_pagado(self):
        socio = crear_socio()
        pagar(socio, 2026, 9)
        respuesta = self.client.post(
            f'/api/socios/{socio.id}/pagar/', {'mes': 9, 'anio': 2026}, format='json')
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Pago.objects.count(), 1)

    def test_pagar_pide_mes_y_anio_juntos(self):
        socio = crear_socio()
        respuesta = self.client.post(f'/api/socios/{socio.id}/pagar/', {'mes': 9}, format='json')
        self.assertEqual(respuesta.status_code, 400)

    def test_pago_repetido_por_api_de_pagos(self):
        socio = crear_socio()
        datos = {'socio': socio.id, 'mes': 9, 'anio': 2026, 'monto': '5000'}
        self.assertEqual(self.client.post('/api/pagos/', datos, format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/pagos/', datos, format='json').status_code, 400)


class HistorialYSociosInactivosTests(APITestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('secretaria', password='clave12345', is_staff=True)
        self.client.force_authenticate(self.usuario)

    def test_socio_inactivo_no_debe_ni_tiene_link(self):
        socio = crear_socio(activo=False)
        with con_fecha(2026, 11, 19):
            self.assertEqual(socio.meses_adeudados(), [])
            self.assertIsNone(socio.link_whatsapp())
            respuesta = self.client.get('/api/socios/')
        self.assertEqual(respuesta.data['results'][0]['estado'], 'inactivo')
        self.assertIsNone(respuesta.data['results'][0]['link_whatsapp'])

    def test_inactivo_conserva_su_historial(self):
        socio = crear_socio()
        pagar(socio, 2026, 9)
        respuesta = self.client.patch(f'/api/socios/{socio.id}/', {'activo': False}, format='json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Pago.objects.filter(socio=socio).count(), 1)

    def test_filtro_inactivos_y_resumen(self):
        crear_socio()
        crear_socio(dni='20999888', activo=False)
        with con_fecha(2026, 11, 19):
            inactivos = self.client.get('/api/socios/?estado=inactivo')
            morosos = self.client.get('/api/socios/?estado=moroso')
            resumen = self.client.get('/api/socios/resumen/')
        self.assertEqual(len(inactivos.data['results']), 1)
        self.assertEqual(len(morosos.data['results']), 1)
        self.assertEqual(resumen.data, {'total': 1, 'al_dia': 0, 'morosos': 1, 'inactivos': 1})

    def test_pagar_con_mes_fecha_y_forma_de_pago(self):
        socio = crear_socio()
        datos = {'mes': 10, 'anio': 2026, 'fecha_pago': '2026-11-05',
                 'forma_pago': 'transferencia', 'monto': '10000'}
        with con_fecha(2026, 11, 19):
            respuesta = self.client.post(f'/api/socios/{socio.id}/pagar/', datos, format='json')
        self.assertEqual(respuesta.status_code, 201)
        pago = Pago.objects.get()
        self.assertEqual((pago.mes, pago.anio), (10, 2026))
        self.assertEqual(pago.fecha_pago, date(2026, 11, 5))
        self.assertEqual(pago.forma_pago, 'transferencia')

    def test_forma_de_pago_invalida(self):
        socio = crear_socio()
        respuesta = self.client.post(
            f'/api/socios/{socio.id}/pagar/', {'forma_pago': 'cheque'}, format='json')
        self.assertEqual(respuesta.status_code, 400)

    def test_ficha_trae_historial_ordenado(self):
        socio = crear_socio()
        pagar(socio, 2026, 9)
        pagar(socio, 2026, 11)
        pagar(socio, 2026, 10)
        respuesta = self.client.get(f'/api/socios/{socio.id}/')
        pagos = respuesta.data['pagos']
        self.assertEqual([p['mes'] for p in pagos], [11, 10, 9])
        self.assertEqual(pagos[0]['mes_nombre'], 'Noviembre')
        self.assertEqual(pagos[0]['forma_pago_nombre'], 'Efectivo')
        self.assertIn('proximo_periodo', respuesta.data)

    def test_eliminar_un_pago(self):
        socio = crear_socio()
        pago = pagar(socio, 2026, 9)
        self.assertEqual(self.client.delete(f'/api/pagos/{pago.id}/').status_code, 204)
        self.assertEqual(Pago.objects.count(), 0)


class ExportarExcelTests(APITestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('secretaria', password='clave12345', is_staff=True)
        self.client.force_authenticate(self.usuario)

    def leer(self, respuesta):
        from io import BytesIO
        from openpyxl import load_workbook
        return list(load_workbook(BytesIO(respuesta.content)).active.values)

    def test_descarga_un_excel_con_los_socios(self):
        crear_socio()
        with con_fecha(2026, 11, 19):
            respuesta = self.client.get('/api/socios/exportar/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('.xlsx', respuesta['Content-Disposition'])
        filas = self.leer(respuesta)
        self.assertEqual(filas[0][0], 'Apellido')
        self.assertEqual(filas[1][:4], ('Pérez', 'Juan', '30111222', '3584123456'))
        self.assertEqual(filas[1][7], 'Debe cuota')
        self.assertEqual(filas[1][8], 'Septiembre 2026, Octubre 2026, Noviembre 2026')

    def test_respeta_el_filtro_de_estado(self):
        crear_socio()
        al_dia = crear_socio(dni='20999888', nombre='María')
        for mes in (9, 10, 11):
            pagar(al_dia, 2026, mes)
        with con_fecha(2026, 11, 19):
            respuesta = self.client.get('/api/socios/exportar/?estado=al_dia')
        filas = self.leer(respuesta)
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[1][1], 'María')

    def test_requiere_login(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/socios/exportar/').status_code, (401, 403))


class IngresosTests(APITestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('secretaria', password='clave12345', is_staff=True)
        self.client.force_authenticate(self.usuario)
        self.socio = crear_socio()

    def cobrar(self, mes, anio, fecha, monto, forma='efectivo'):
        return Pago.objects.create(socio=self.socio, mes=mes, anio=anio, monto=monto,
                                   fecha_pago=fecha, forma_pago=forma)

    def test_suma_por_mes_de_cobro_y_forma_de_pago(self):
        # La cuota de septiembre se cobró en octubre: cuenta como ingreso de octubre
        self.cobrar(9, 2026, date(2026, 10, 2), 10000, 'transferencia')
        self.cobrar(10, 2026, date(2026, 10, 20), 5000, 'efectivo')
        self.cobrar(11, 2026, date(2026, 11, 3), 7000, 'efectivo')
        respuesta = self.client.get('/api/pagos/ingresos/?anio=2026')
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.data
        self.assertEqual(len(datos['meses']), 12)
        octubre = datos['meses'][9]
        self.assertEqual((octubre['mes_nombre'], octubre['cantidad']), ('Octubre', 2))
        self.assertEqual(float(octubre['total']), 15000)
        self.assertEqual(float(octubre['transferencia']), 10000)
        self.assertEqual(float(octubre['efectivo']), 5000)
        self.assertEqual(float(datos['meses'][10]['total']), 7000)
        self.assertEqual(float(datos['meses'][0]['total']), 0)
        self.assertEqual(float(datos['total']), 22000)
        self.assertEqual(datos['cantidad'], 3)

    def test_filtra_por_anio_y_lista_los_anios_disponibles(self):
        self.cobrar(12, 2025, date(2025, 12, 5), 4000)
        self.cobrar(1, 2026, date(2026, 1, 5), 6000)
        datos = self.client.get('/api/pagos/ingresos/?anio=2025').data
        self.assertEqual(float(datos['total']), 4000)
        self.assertIn(2026, datos['anios'])
        self.assertIn(2025, datos['anios'])

    def test_sin_anio_usa_el_actual(self):
        with con_fecha(2026, 11, 19):
            datos = self.client.get('/api/pagos/ingresos/').data
        self.assertEqual(datos['anio'], 2026)

    def test_anio_invalido(self):
        self.assertEqual(self.client.get('/api/pagos/ingresos/?anio=abc').status_code, 400)

    def test_requiere_login(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get('/api/pagos/ingresos/').status_code, (401, 403))

    def test_pagina_de_ingresos_solo_para_staff(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/ingresos/').status_code, 302)
        self.client.login(username='secretaria', password='clave12345')
        respuesta = self.client.get('/ingresos/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Ingresos por mes')
        self.assertContains(respuesta, 'Club La Lonja (C.A.L.L.)')  # pie de base.html


class PantallaPrincipalTests(TestCase):
    def test_sin_login_manda_al_ingreso(self):
        respuesta = self.client.get(reverse('home'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/admin/login/', respuesta['Location'])

    def test_usuario_sin_permiso_de_staff_no_entra(self):
        User.objects.create_user('socio', password='clave12345')
        self.client.login(username='socio', password='clave12345')
        self.assertEqual(self.client.get(reverse('home')).status_code, 302)

    def test_secretaria_ve_la_pantalla(self):
        User.objects.create_user('secretaria', password='clave12345', is_staff=True)
        self.client.login(username='secretaria', password='clave12345')
        respuesta = self.client.get(reverse('home'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Club La Lonja')
        self.assertContains(respuesta, 'const MONTO_CUOTA = 5000;')

    def test_ficha_del_socio_usa_la_misma_pagina(self):
        socio = crear_socio()
        User.objects.create_user('secretaria', password='clave12345', is_staff=True)
        self.assertEqual(self.client.get(f'/socios/{socio.id}/').status_code, 302)
        self.client.login(username='secretaria', password='clave12345')
        self.assertEqual(self.client.get(f'/socios/{socio.id}/').status_code, 200)
