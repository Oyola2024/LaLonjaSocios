from rest_framework import serializers
from .models import Socio, Pago, nombre_periodo


class SocioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Socio
        fields = [
            'id',
            'nombre',
            'apellido',
            'dni',
            'telefono',
            'email',
            'direccion',
            'fecha_alta',
            'activo',
        ]

        read_only_fields = ['id']

    def validate_telefono(self, value):
        digitos = ''.join(c for c in value if c.isdigit())
        if not 8 <= len(digitos) <= 15:
            raise serializers.ValidationError('Ingresá un teléfono válido, con código de área y sin el 15.')
        return digitos

class SocioEstadoSerializer(serializers.ModelSerializer):
    estado = serializers.SerializerMethodField()
    meses_adeudados = serializers.SerializerMethodField()
    proximo_mes_a_pagar = serializers.SerializerMethodField()
    proximo_periodo = serializers.SerializerMethodField()
    ultimo_pago = serializers.SerializerMethodField()

    class Meta:
        model = Socio
        fields = [
            'id',
            'nombre',
            'apellido',
            'dni',
            'telefono',
            'email',
            'direccion',
            'fecha_alta',
            'activo',
            'estado',
            'meses_adeudados',
            'proximo_mes_a_pagar',
            'proximo_periodo',
            'ultimo_pago',
        ]

        read_only_fields = ['id']

    def get_estado(self, socio) -> str:
        if not socio.activo:
            return 'inactivo'
        return 'al_dia' if socio.al_dia else 'moroso'

    def get_meses_adeudados(self, socio) -> list[str]:
        return [nombre_periodo(anio, mes) for anio, mes in socio.meses_adeudados()]

    def get_proximo_mes_a_pagar(self, socio) -> str:
        return nombre_periodo(*socio.proximo_mes_a_pagar())

    def get_proximo_periodo(self, socio) -> dict:
        anio, mes = socio.proximo_mes_a_pagar()
        return {'mes': mes, 'anio': anio}

    def get_ultimo_pago(self, socio) -> str | None:
        pago = socio.ultimo_pago()
        return pago.fecha_pago.isoformat() if pago else None

class PagoSerializer(serializers.ModelSerializer):
    mes_nombre = serializers.CharField(source='get_mes_display', read_only=True)
    forma_pago_nombre = serializers.CharField(source='get_forma_pago_display', read_only=True)

    class Meta:
        model = Pago
        fields = [
            'id',
            'socio',
            'mes',
            'mes_nombre',
            'anio',
            'monto',
            'fecha_pago',
            'forma_pago',
            'forma_pago_nombre',
        ]

        read_only_fields = ['id']


# Ficha del socio: los mismos datos del listado más su historial de pagos
class SocioDetalleSerializer(SocioEstadoSerializer):
    pagos = PagoSerializer(many=True, read_only=True)

    class Meta(SocioEstadoSerializer.Meta):
        fields = SocioEstadoSerializer.Meta.fields + ['pagos']


class ResumenSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    al_dia = serializers.IntegerField()
    morosos = serializers.IntegerField()
    inactivos = serializers.IntegerField()