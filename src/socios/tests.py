from datetime import date
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.test import TestCase

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