from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from .models import TareaAutomatizacion, RecursoSemana, CredencialMoodle
from .services import correr_bot_moodle
import threading
import os
import json

def dashboard(request):
    tareas_existentes = TareaAutomatizacion.objects.all().order_by('-id')
    
    if request.method == 'POST':
        json_data_str = request.POST.get('json_data')
        try:
            data = json.loads(json_data_str)
            curso_nombre = data.get('curso_nombre')
            if not curso_nombre:
                raise ValueError("El JSON debe contener 'curso_nombre'")
            
            tarea, _ = TareaAutomatizacion.objects.get_or_create(
                curso_nombre=curso_nombre
            )
            if 'titulo_general' in data:
                tarea.titulo_general = data['titulo_general']
            if 'mensaje_avisos' in data:
                tarea.mensaje_avisos = data['mensaje_avisos']
            tarea.esta_activa = True
            tarea.save()
            
            for sem in data.get('semanas', []):
                recurso, _ = RecursoSemana.objects.get_or_create(
                    tarea=tarea,
                    semana_numero=sem.get('numero', 1)
                )
                if 'titulo' in sem:
                    recurso.titulo = sem['titulo']
                if 'texto' in sem:
                    recurso.texto = sem['texto']
                recurso.save()
                
            return redirect('moodle:dashboard')
        except Exception as e:
            return render(request, 'moodle/dashboard.html', {'error_json': f"Error en el JSON: {str(e)}", 'tareas': tareas_existentes})

    return render(request, 'moodle/dashboard.html', {'tareas': tareas_existentes})

def course_detail(request, tarea_id):
    tarea = get_object_or_404(TareaAutomatizacion, id=tarea_id)
    recursos = tarea.recursos_semanas.all().order_by('semana_numero')
    
    if request.method == 'POST':
        recurso_id = request.POST.get('recurso_id')
        recurso = get_object_or_404(RecursoSemana, id=recurso_id, tarea=tarea)
        
        # Crear directorio si no existe
        upload_dir = f'media/moodle_uploads/curso_{tarea.id}/semana_{recurso.semana_numero}'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        fs = FileSystemStorage(location=upload_dir)
        
        def guardar_archivos(lista_archivos):
            rutas = []
            for f in lista_archivos:
                filename = fs.save(f.name, f)
                # Usamos ruta absoluta para que Playwright la encuentre
                rutas.append(os.path.abspath(fs.path(filename)))
            return rutas

        # Extraemos las carpetas existentes o iniciamos vacío
        archivos_json = recurso.archivos_carpetas or {}
        
        desarrollo_files = request.FILES.getlist('desarrollo')
        if desarrollo_files:
            archivos_json['desarrollo'] = guardar_archivos(desarrollo_files)
            
        analisis_files = request.FILES.getlist('analisis')
        if analisis_files:
            archivos_json['analisis'] = guardar_archivos(analisis_files)
            
        evaluacion_files = request.FILES.getlist('evaluacion')
        if evaluacion_files:
            archivos_json['evaluacion'] = guardar_archivos(evaluacion_files)
            
        recurso.archivos_carpetas = archivos_json
        recurso.save()
        
        return redirect('moodle:course_detail', tarea_id=tarea.id)
        
    return render(request, 'moodle/course_detail.html', {'tarea': tarea, 'recursos': recursos})

def run_bot_view(request, tarea_id):
    if CredencialMoodle.objects.filter(esta_activa=True).exists():
        thread = threading.Thread(target=correr_bot_moodle, args=(tarea_id,))
        thread.start()
    return redirect('moodle:course_detail', tarea_id=tarea_id)
