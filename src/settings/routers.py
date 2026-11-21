from rest_framework.routers import DefaultRouter
from socios.views import (
    SocioViewSet,
    PagoViewSet,
)

router = DefaultRouter()
router.register(r'socios', SocioViewSet)
router.register(r'pagos', PagoViewSet)
