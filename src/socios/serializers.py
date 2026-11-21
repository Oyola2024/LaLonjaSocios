from rest_framework import serializers
from .models import Socio, Pago


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