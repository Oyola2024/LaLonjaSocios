@echo off
cd /d %~dp0
uv sync || goto :error
uv run python manage.py collectstatic --noinput || goto :error
uv run pyinstaller lanzador.py --name LaLonja --noconfirm --onedir --console ^
  --add-data "templates;templates" --add-data "staticfiles;staticfiles" ^
  --collect-all django --collect-submodules rest_framework ^
  --collect-submodules rest_framework_simplejwt ^
  --collect-all drf_spectacular --collect-submodules django_filters ^
  --collect-submodules socios --collect-submodules settings ^
  --collect-data tzdata --collect-submodules whitenoise ^
  --collect-submodules openpyxl || goto :error
echo.
echo Listo. El programa quedo en dist\LaLonja\LaLonja.exe
pause
exit /b 0
:error
echo.
echo Algo fallo. Copia el mensaje de arriba y pasaselo a quien armo el proyecto.
pause
exit /b 1