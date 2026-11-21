from .models import Socio, Pago
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter


from .serializers import (
    SocioSerializer,
    SocioEstadoSerializer,
    SocioDetalleSerializer,
    PagoSerializer,
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
    queryset = Socio.objects.all().order_by('apellido', 'nombre')
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
        if self.action == 'list' and estado == 'inactivo':
            queryset = queryset.filter(activo=False)
        elif self.action == 'list' and estado in ('al_dia', 'moroso'):
            # El estado se calcula con los pagos, por eso se filtra en Python
            activos = queryset.filter(activo=True)
            ids = [socio.id for socio in activos if socio.al_dia == (estado == 'al_dia')]
            queryset = queryset.filter(id__in=ids)
        return queryset

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



    
class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all().select_related('socio').order_by('-anio', '-mes')
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['socio', 'mes', 'anio', 'forma_pago']