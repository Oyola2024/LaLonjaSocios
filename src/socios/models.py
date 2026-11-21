from urllib.parse import quote

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


MESES = [
    (1, 'Enero'),
    (2, 'Febrero'),
    (3, 'Marzo'),
    (4, 'Abril'),
    (5, 'Mayo'),
    (6, 'Junio'),
    (7, 'Julio'),
    (8, 'Agosto'),
    (9, 'Septiembre'),
    (10, 'Octubre'),
    (11, 'Noviembre'),
    (12, 'Diciembre'),
]


def hoy():
    return timezone.localdate()


def mes_siguiente(anio, mes):
    return (anio + 1, 1) if mes == 12 else (anio, mes + 1)


def mes_anterior(anio, mes):
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def nombre_periodo(anio, mes):
    return f"{dict(MESES)[mes]} {anio}"


class Socio(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(
        max_length=8,
        unique=True,
        error_messages={'unique': 'Ya hay un socio registrado con ese DNI.'},
        validators=[RegexValidator(r'^\d{7,8}$', 'El DNI debe tener 7 u 8 números, sin puntos.')],
    )
    telefono = models.CharField(
        max_length=20,
        help_text='Número de WhatsApp con código de área y sin el 15. Ej: 3584123456',
    )
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    fecha_alta = models.DateField(default=hoy)
    # Se destilda cuando el socio se da de baja pero se quiere conservar su historial
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    # ---- Estado de la cuota ----
    # La cuota de cada mes vence el día DIA_VENCIMIENTO (el 3).
    # Un mes está "vencido" cuando ya pasó ese día. Se debe todo mes vencido
    # desde el mes de alta del socio que no tenga un pago registrado.

    def _periodos_pagados(self):
        # .all() aprovecha prefetch_related('pagos') si la vista lo hizo
        return {(pago.anio, pago.mes) for pago in self.pagos.all()}

    def _ultimo_mes_vencido(self):
        fecha = hoy()
        if fecha.day > settings.DIA_VENCIMIENTO:
            return (fecha.year, fecha.month)
        return mes_anterior(fecha.year, fecha.month)

    def meses_adeudados(self):
        if not self.activo:
            return []
        pagados = self._periodos_pagados()
        limite = self._ultimo_mes_vencido()
        periodo = (self.fecha_alta.year, self.fecha_alta.month)
        deuda = []
        while periodo <= limite:
            if periodo not in pagados:
                deuda.append(periodo)
            periodo = mes_siguiente(*periodo)
        return deuda

    @property
    def al_dia(self):
        return not self.meses_adeudados()

    def proximo_mes_a_pagar(self):
        deuda = self.meses_adeudados()
        if deuda:
            return deuda[0]
        pagados = self._periodos_pagados()
        periodo = mes_siguiente(*self._ultimo_mes_vencido())
        while periodo in pagados:
            periodo = mes_siguiente(*periodo)
        return periodo

    def ultimo_pago(self):
        pagos = list(self.pagos.all())
        if not pagos:
            return None
        return max(pagos, key=lambda pago: (pago.anio, pago.mes))

    # ---- Aviso por WhatsApp ----

    def telefono_whatsapp(self):
        """Devuelve el teléfono listo para wa.me (código de país 54 + 9 + área + número)."""
        digitos = ''.join(c for c in self.telefono if c.isdigit()).lstrip('0')
        if digitos.startswith('54'):
            if not digitos.startswith('549'):
                digitos = '549' + digitos[2:]
            return digitos
        return '549' + digitos

    def link_whatsapp(self):
        deuda = [nombre_periodo(anio, mes) for anio, mes in self.meses_adeudados()]
        if not self.activo or not deuda:
            return None
        if len(deuda) == 1:
            detalle = deuda[0]
        else:
            detalle = ', '.join(deuda[:-1]) + ' y ' + deuda[-1]
        mensaje = (
            f"Hola {self.nombre}, te escribimos de la secretaría del Club La Lonja. "
            f"Te recordamos que la cuota social vence el día {settings.DIA_VENCIMIENTO} de cada mes "
            f"y figura pendiente: {detalle}. "
            f"Podés acercarte a abonarla en la secretaría. ¡Gracias!"
        )
        return f"https://wa.me/{self.telefono_whatsapp()}?text={quote(mensaje)}"


FORMAS_DE_PAGO = [
    ('efectivo', 'Efectivo'),
    ('transferencia', 'Transferencia'),
]


class Pago(models.Model):
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='pagos')
    mes = models.PositiveSmallIntegerField(choices=MESES)
    anio = models.PositiveSmallIntegerField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateField(default=hoy)
    forma_pago = models.CharField(max_length=20, choices=FORMAS_DE_PAGO, default='efectivo')

    class Meta:
        ordering = ['-anio', '-mes']
        constraints = [
            models.UniqueConstraint(
                fields=['socio', 'mes', 'anio'],
                name='un_pago_por_socio_y_mes',
                violation_error_message='Ese mes ya tiene un pago registrado para este socio.',
            ),
        ]

    def __str__(self):
        return f"Pago de {self.socio} - {self.get_mes_display()} {self.anio}"
