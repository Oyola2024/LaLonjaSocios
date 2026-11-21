from .models import Socio, Pago
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter


from .serializers import (
    SocioSerializer,
    PagoSerializer,
)

from django.http import HttpResponse

def home(request):
    return HttpResponse("Inicio")

def ingresos(request):
    return HttpResponse("Ingresos")

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


class PagoViewSet(viewsets.ModelViewSet):
    queryset = Pago.objects.all().select_related('socio').order_by('-anio', '-mes')
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['socio', 'mes', 'anio', 'forma_pago']