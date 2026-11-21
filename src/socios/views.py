from io import BytesIO

from django.conf import settings
from django.http import HttpResponse
from .models import Socio, Pago, hoy, nombre_periodo
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from openpyxl import Workbook
from openpyxl.styles import Font
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse


from .serializers import (
    SocioSerializer,
    SocioEstadoSerializer,
    SocioDetalleSerializer,
    PagoSerializer,
    PagarSerializer,
    ResumenSerializer,
)

from django.http import HttpResponse

def home(request):
    return HttpResponse("Inicio")

def ingresos(request):
    return HttpResponse("Ingresos")


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                'estado', str, enum=['al_dia', 'moroso', 'inactivo'],
                description="Filtra por estado: 'al_dia', 'moroso' (deben cuota) o 'inactivo' (dados de baja).",
            ),
        ],
    ),
)
class SocioViewSet(viewsets.ModelViewSet):
    queryset = Socio.objects.all().prefetch_related('pagos').order_by('apellido', 'nombre')
    serializer_class = SocioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = ['apellido', 'nombre', 'fecha_alta']

    filterset_fields = {
        'nombre': ['icontains'],
        'apellido': ['icontains'],
        'dni': ['exact', 'icontains'],
        'telefono': ['icontains'],
    }

    search_fields = ['nombre', 'apellido', 'dni']

    def get_queryset(self):
        queryset = super().get_queryset()
        estado = self.request.query_params.get('estado') if self.request else None
        if self.action in ('list', 'exportar') and estado == 'inactivo':
            queryset = queryset.filter(activo=False)
        elif self.action in ('list', 'exportar') and estado in ('al_dia', 'moroso'):
            # El estado se calcula con los pagos, por eso se filtra en Python
            activos = queryset.filter(activo=True)
            ids = [socio.id for socio in activos if socio.al_dia == (estado == 'al_dia')]
            queryset = queryset.filter(id__in=ids)
        return queryset

    # Datos de la cuota (estado, meses adeudados, link de WhatsApp) en list;
    # en retrieve además va el historial de pagos
    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return SocioSerializer
        if self.action == 'retrieve':
            return SocioDetalleSerializer
        return SocioEstadoSerializer

    @extend_schema(
        summary="Resumen de socios",
        description="Socios activos, los que están al día, los que deben cuota y los inactivos (dados de baja).",
        responses=ResumenSerializer,
    )
    @action(detail=False, methods=['get'])
    def resumen(self, request):
        socios = list(Socio.objects.all().prefetch_related('pagos'))
        activos = [socio for socio in socios if socio.activo]
        al_dia = sum(1 for socio in activos if socio.al_dia)
        return Response({
            'total': len(activos),
            'al_dia': al_dia,
            'morosos': len(activos) - al_dia,
            'inactivos': len(socios) - len(activos),
        })

    @extend_schema(
        summary="Descargar los socios en Excel",
        description="Archivo .xlsx con los socios. Respeta los mismos filtros que el listado (estado, search).",
        parameters=[
            OpenApiParameter('estado', str, enum=['al_dia', 'moroso', 'inactivo']),
        ],
        responses={
            (200, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'): OpenApiTypes.BINARY,
        },
    )
    @action(detail=False, methods=['get'])
    def exportar(self, request):
        socios = self.filter_queryset(self.get_queryset())

        libro = Workbook()
        hoja = libro.active
        hoja.title = 'Socios'
        hoja.append([
            'Apellido', 'Nombre', 'DNI', 'WhatsApp', 'Email', 'Dirección',
            'Fecha de alta', 'Estado', 'Meses adeudados', 'Último pago',
        ])
        for celda in hoja[1]:
            celda.font = Font(bold=True)

        estados = {'al_dia': 'Al día', 'moroso': 'Debe cuota', 'inactivo': 'Inactivo'}
        for socio in socios:
            if not socio.activo:
                estado = 'inactivo'
            else:
                estado = 'al_dia' if socio.al_dia else 'moroso'
            pago = socio.ultimo_pago()
            hoja.append([
                socio.apellido,
                socio.nombre,
                socio.dni,
                socio.telefono,
                socio.email or '',
                socio.direccion or '',
                socio.fecha_alta,
                estados[estado],
                ', '.join(nombre_periodo(anio, mes) for anio, mes in socio.meses_adeudados()),
                pago.fecha_pago if pago else '',
            ])

        for columna, ancho in zip('ABCDEFGHIJ', (18, 18, 12, 16, 28, 28, 14, 14, 36, 14)):
            hoja.column_dimensions[columna].width = ancho
        for fila in hoja.iter_rows(min_row=2):
            fila[6].number_format = 'DD/MM/YYYY'
            fila[9].number_format = 'DD/MM/YYYY'

        archivo = BytesIO()
        libro.save(archivo)
        respuesta = HttpResponse(
            archivo.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        respuesta['Content-Disposition'] = f'attachment; filename="socios-{hoy().isoformat()}.xlsx"'
        return respuesta

    @extend_schema(
        summary="Registrar el pago de una cuota",
        description=(
            "Registra un pago del socio. Sin body paga la próxima cuota que corresponde "
            "(la más vieja adeudada) por el monto de la cuota. Opcionalmente se puede indicar "
            "mes, año, monto, fecha_pago y forma_pago (efectivo o transferencia)."
        ),
        request=PagarSerializer,
        responses={
            201: SocioDetalleSerializer,
            400: OpenApiResponse(description="Datos inválidos o cuota ya pagada"),
            404: OpenApiResponse(description="Socio no encontrado"),
        }
    )
    @action(detail=True, methods=['post'])
    def pagar(self, request, pk=None):
        socio = self.get_object()
        entrada = PagarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        if 'mes' in datos:
            anio, mes = datos['anio'], datos['mes']
        else:
            anio, mes = socio.proximo_mes_a_pagar()

        if socio.pagos.filter(anio=anio, mes=mes).exists():
            return Response(
                {'detail': f"Ya está registrado el pago de {nombre_periodo(anio, mes)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Pago.objects.create(
            socio=socio,
            anio=anio,
            mes=mes,
            monto=datos.get('monto', settings.MONTO_CUOTA),
            fecha_pago=datos.get('fecha_pago', hoy()),
            forma_pago=datos.get('forma_pago', 'efectivo'),
        )
        # Se vuelve a leer el socio para que el estado salga actualizado
        socio = Socio.objects.prefetch_related('pagos').get(pk=socio.pk)
        return Response(SocioDetalleSerializer(socio).data, status=status.HTTP_201_CREATED)


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all().select_related('socio').order_by('-anio', '-mes')
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['socio', 'mes', 'anio', 'forma_pago']