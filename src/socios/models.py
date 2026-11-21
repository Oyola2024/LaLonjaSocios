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
