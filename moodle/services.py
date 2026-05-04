import os
from playwright.sync_api import sync_playwright, Page
import time
from django.utils import timezone
from .models import CredencialMoodle, TareaAutomatizacion
from .recursos import agregar_area_texto_semana, agregar_carpetas_semana, subir_archivos_a_carpetas

# Permitir llamadas síncronas a la BD dentro del contexto de Playwright
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

# ─────────────────────────────────────────────
#  Paso 1: Login
# ─────────────────────────────────────────────
def _hacer_login(page: Page, usuario: str, contrasena: str):
    print("🌐 Navegando a la página de login...")
    page.goto(
        "https://marello.edu.pe/aulavirtual/login/index.php",
        timeout=60000,
        wait_until="domcontentloaded"
    )
    page.fill("input#username", usuario)
    page.fill("input#password", contrasena)
    page.click("button#loginbtn")
    page.wait_for_load_state("domcontentloaded")
    print("✅ Login exitoso.")


# ─────────────────────────────────────────────
#  Paso 2: Entrar al curso → Activar modo edición
# ─────────────────────────────────────────────
def _navegar_curso_y_activar_edicion(page: Page, nombre_curso: str):
    print("📂 Navegando a Mis cursos...")
    page.goto(
        "https://marello.edu.pe/aulavirtual/my/courses.php",
        timeout=60000,
        wait_until="domcontentloaded"
    )
    
    print(f"📚 Buscando el curso: '{nombre_curso}'...")
    page.wait_for_selector(".card-grid", timeout=60000)

    course_link = page.locator(".card-grid a.aalink.coursename", has_text=nombre_curso)
    course_url = course_link.get_attribute("href")
    
    page.goto(course_url, timeout=60000, wait_until="domcontentloaded")
    print(f"✅ Dentro del curso: {nombre_curso}")

    print("✏️  Activando Modo de edición...")
    edit_checkbox = page.locator("input[name='setmode']")
    edit_checkbox.wait_for(timeout=30000)

    if not edit_checkbox.is_checked():
        page.evaluate("document.querySelector(\"input[name='setmode']\").click()")
        page.wait_for_load_state("domcontentloaded")
        print("✅ Modo de edición activado.")
    else:
        print("ℹ️  El modo de edición ya estaba activo.")


# ─────────────────────────────────────────────
#  Paso 3: Editar nombre de "General"
# ─────────────────────────────────────────────
def _editar_nombre_seccion_general(page: Page, nuevo_nombre: str):
    print(f"✏️  Editando nombre de la sección General → '{nuevo_nombre}'...")
    
    # Validamos si ya tiene el nombre correcto leyendo el atributo data-value
    span_general = page.locator('[data-for="section_title"][data-number="0"] span.inplaceeditable')
    span_general.wait_for(timeout=15000)
    
    texto_actual = span_general.get_attribute("data-value")
    if texto_actual == nuevo_nombre:
        print("⏭️  El título ya es correcto. Omitiendo edición...")
        return
    
    lapiz_general = page.locator('[data-for="section_title"][data-number="0"] a.quickeditlink')
    lapiz_general.wait_for(timeout=15000)
    page.evaluate('document.querySelector(\'[data-for="section_title"][data-number="0"] a.quickeditlink\').click()')

    input_inline = page.locator('[data-for="section_title"][data-number="0"] input[type="text"]')
    input_inline.wait_for(timeout=10000)
    input_inline.click(click_count=3)
    input_inline.press("Backspace")
    input_inline.fill(nuevo_nombre)
    input_inline.press("Enter")

    page.wait_for_selector('[data-for="section_title"][data-number="0"] input[type="text"]', state="detached", timeout=15000)
    print("✅ Nombre de sección General actualizado.")


# ─────────────────────────────────────────────
#  Paso 4: Editar Avisos
# ─────────────────────────────────────────────
def _editar_nombre_avisos(page: Page, nuevo_mensaje: str):
    # Moodle limits activity names (like Avisos) and throws an exception dialog if too long
    if len(nuevo_mensaje) > 200:
        nuevo_mensaje = nuevo_mensaje[:197] + "..."
        
    print(f"✏️  Editando texto de Avisos → '{nuevo_mensaje}'...")
    
    # Buscamos el primer span de actividad (que por defecto es Avisos)
    span_avisos = page.locator('span.inplaceeditable[data-itemtype="activityname"]').first
    span_avisos.wait_for(timeout=15000)
    
    texto_actual = span_avisos.get_attribute("data-value")
    if texto_actual == nuevo_mensaje:
        print("⏭️  El texto de avisos ya es correcto. Omitiendo edición...")
        return

    # Buscamos el primer lápiz de las actividades
    lapiz_avisos = span_avisos.locator('a.quickeditlink')
    lapiz_avisos.wait_for(timeout=15000)
    
    # Clic vía JS (usamos querySelector en lugar del locator puro para que sea infalible)
    page.evaluate('document.querySelector(\'span.inplaceeditable[data-itemtype="activityname"] a.quickeditlink\').click()')

    input_inline = page.locator('span.inplaceeditable[data-itemtype="activityname"] input[type="text"]').first
    input_inline.wait_for(timeout=10000)
    input_inline.click(click_count=3)
    input_inline.press("Backspace")
    input_inline.fill(nuevo_mensaje)
    input_inline.press("Enter")

    page.wait_for_selector('span.inplaceeditable[data-itemtype="activityname"] input[type="text"]', state="detached", timeout=15000)
    print("✅ Texto de Avisos actualizado.")


# ─────────────────────────────────────────────
#  Paso 5: Renombrar Secciones de Semanas
# ─────────────────────────────────────────────
def _renombrar_secciones_semanas(page: Page):
    print("\n📅 Iniciando renombrado de las secciones por semana...")
    
    i = 1
    while True:
        # Buscamos explícitamente el contenedor de título para el data-number exacto
        titulo = page.locator(f'[data-for="section_title"][data-number="{i}"]')
        
        # Si no encontramos el data-number, significa que ya no hay más semanas
        if titulo.count() == 0:
            break
            
        titulo = titulo.first
        span_edit = titulo.locator('span.inplaceeditable')
        
        if span_edit.count() == 0:
            i += 1
            continue
            
        # Extraemos el texto exacto actual mediante JS
        texto_actual = titulo.evaluate('''
            (el) => {
                const a = el.querySelector("a.quickeditlink");
                if (!a) return "";
                let text = "";
                for (let node of a.childNodes) {
                    if (node.nodeType === 3) {
                        text += node.textContent;
                    }
                }
                return text.trim();
            }
        ''')
        
        marcador = f"Semana {i}"
        
        # Si ya es exactamente el nombre que queremos, saltamos
        if texto_actual.strip() == marcador:
            print(f"⏭️  Sección {i} ya tiene formato correcto ('{texto_actual}'). Omitiendo...")
            i += 1
            continue
            
        nuevo_nombre = marcador
        print(f"✏️  Renombrando sección {i} → '{nuevo_nombre}'...")
        
        # Hacemos scroll para asegurarnos de que la sección esté visible en pantalla
        titulo.scroll_into_view_if_needed()
        page.wait_for_timeout(500) # Pequeña pausa por si hay cabeceras pegajosas (sticky headers)
        
        # Hacemos clic en el lápiz usando JS para evitar bloqueos
        titulo.evaluate('(el) => el.querySelector("a.quickeditlink").click()')
        
        # Esperamos al input
        input_inline = titulo.locator('input[type="text"]')
        input_inline.wait_for(timeout=10000)
        
        # Aseguramos que Playwright enfoque el input antes de escribir
        input_inline.focus()
        input_inline.click(click_count=3)
        input_inline.press("Backspace")
        input_inline.fill(nuevo_nombre)
        input_inline.press("Enter")
        
        # Esperar a que se guarde (el input desaparece)
        input_inline.wait_for(state="detached", timeout=15000)
        
        # Pequeña pausa para que Moodle termine sus recargas AJAX tras la actualización
        page.wait_for_timeout(1500)
        
        print(f"✅ Sección {i} renombrada.")
        i += 1


# ─────────────────────────────────────────────
#  Orquestador principal
# ─────────────────────────────────────────────
def correr_bot_moodle(tarea_id=None):
    cuenta = CredencialMoodle.objects.filter(esta_activa=True).first()
    if not cuenta:
        print("❌ No hay cuentas de Moodle activas en la BD.")
        return

    # Traemos las tareas desde la BD (Django Admin)
    if tarea_id:
        tareas = TareaAutomatizacion.objects.filter(id=tarea_id)
    else:
        tareas = TareaAutomatizacion.objects.filter(esta_activa=True)
        
    if not tareas.exists():
        print("❌ No hay tareas de automatización activas en la BD.")
        return

    usuario = cuenta.usuario
    contrasena = cuenta.contrasena
    cuenta_id = cuenta.id

    exito = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=600)
        page = browser.new_page()

        try:
            # Login una sola vez
            _hacer_login(page, usuario, contrasena)
            exito = True

            # Procesamos cada curso configurado en el panel
            for tarea in tareas:
                try:
                    print(f"\n======================================")
                    print(f"🚀 INICIANDO TAREA: {tarea.curso_nombre}")
                    print(f"======================================")
                    
                    _navegar_curso_y_activar_edicion(page, tarea.curso_nombre)
                    _editar_nombre_seccion_general(page, tarea.titulo_general)
                    _editar_nombre_avisos(page, tarea.mensaje_avisos)
                    _renombrar_secciones_semanas(page)
                    
                    # Guardamos la URL del curso para regresar a ella después de cada subida
                    curso_url = page.url
                    
                    # Agregamos los recursos para cada semana configurada en base de datos
                    recursos = tarea.recursos_semanas.all()
                    for recurso in recursos:
                        print(f"\n======================================")
                        print(f"   Procesando Semana {recurso.semana_numero}")
                        print(f"======================================")
                        
                        try:
                            agregar_area_texto_semana(page, recurso.semana_numero, recurso.titulo, recurso.texto)
                        except Exception as e:
                            print(f"⚠️ Error al agregar área de texto en Semana {recurso.semana_numero}: {e}")
                            page.goto(curso_url)
                            page.wait_for_load_state("domcontentloaded")
                            page.wait_for_timeout(3000)
                            
                        try:
                            agregar_carpetas_semana(page, recurso.semana_numero, curso_url)
                        except Exception as e:
                            print(f"⚠️ Error general al procesar carpetas en Semana {recurso.semana_numero}: {e}")
                            page.goto(curso_url)
                            page.wait_for_load_state("domcontentloaded")
                            page.wait_for_timeout(3000)
                            
                        try:
                            subir_archivos_a_carpetas(page, recurso.semana_numero, recurso.archivos_carpetas, curso_url)
                        except Exception as e:
                            print(f"⚠️ Error al subir archivos en Semana {recurso.semana_numero}: {e}")
                            page.goto(curso_url)
                            page.wait_for_load_state("domcontentloaded")
                            page.wait_for_timeout(3000)
                    
                    # Actualizamos la última ejecución
                    tarea.ultima_ejecucion = timezone.now()
                    tarea.save()
                    print(f"🎉 Tarea de {tarea.curso_nombre} completada.")
                    
                except Exception as e:
                    print(f"❌ Error al procesar el curso {tarea.curso_nombre}: {e}")

            print("\n✅ Todas las tareas finalizadas. Esperando 5 segundos...")
            time.sleep(5)

        except Exception as e:
            print(f"❌ Error crítico del bot: {e}")
        finally:
            browser.close()

    if exito:
        CredencialMoodle.objects.filter(id=cuenta_id).update(ultima_conexion=timezone.now())
