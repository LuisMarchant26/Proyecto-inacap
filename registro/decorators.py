# registro/decorators.py
from django.shortcuts import redirect
from django.contrib import messages

def solo_trabajadores(view_func):
    def wrapper_func(request, *args, **kwargs):
        # Verificamos si tiene perfil y si es TRABAJADOR
        if request.user.is_authenticated and hasattr(request.user, 'perfil'):
            if request.user.perfil.rol == 'TRABAJADOR':
                return view_func(request, *args, **kwargs)
        
        # Si no es trabajador, lo echamos al login o al admin
        messages.error(request, "No tienes permiso para ver esta sección.")
        return redirect('admin:index') # O al login
    return wrapper_func

def solo_jefes(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'perfil'):
            if request.user.perfil.rol in ['JEFE', 'ADMIN']:
                return view_func(request, *args, **kwargs)
        return redirect('home')
    return wrapper_func