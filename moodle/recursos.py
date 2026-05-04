from playwright.sync_api import Page


# ─────────────────────────────────────────────
#  Helper: Expandir sección colapsada
# ─────────────────────────────────────────────
def _expandir_seccion(page: Page, semana_numero: int):
    """
    Moodle colapsa secciones cuando hay muchas semanas.
    Si la sección está cerrada (con el botón '>'), la expande haciendo clic
    en el toggle y espera a que el botón '+ Añadir' sea visible.
    """
    seccion = page.locator(f'li.section.main[data-number="{semana_numero}"]')
    if seccion.count() == 0:
        return

    # Hacemos scroll a la sección con JS (ignora visibilidad del elemento)
    seccion.evaluate('el => el.scrollIntoView({behavior: "instant", block: "center"})')
    page.wait_for_timeout(500)

    # Buscamos el botón toggle de colapso dentro de la sección
    # Moodle 4.x usa un <a> o <button> con clase 'collapse-toggle' o aria-expanded="false"
    toggle = seccion.locator('[aria-expanded="false"]').first
    if toggle.count() > 0:
        print(f"📂 Expandiendo Semana {semana_numero}...")
        toggle.evaluate('el => el.click()')
        page.wait_for_timeout(1500)

    # Después de expandir, hacemos scroll de nuevo para centrar la sección
    seccion.evaluate('el => el.scrollIntoView({behavior: "instant", block: "center"})')
    page.wait_for_timeout(500)


# ─────────────────────────────────────────────
#  Helper: Obtener texto actual de un label
# ─────────────────────────────────────────────
def _obtener_texto_label(page: Page, semana_numero: int) -> str | None:
    """
    Devuelve el texto visible del primer 'Área de texto y medios' (modtype_label)
    en la sección indicada, o None si no existe.
    """
    seccion = page.locator(f'li.section.main[data-number="{semana_numero}"]')
    label = seccion.locator('.modtype_label .no-overflow').first
    if label.count() > 0:
        return label.inner_text().strip()
    return None


def agregar_area_texto_semana(page: Page, semana_numero: int, titulo: str, texto: str):
    """
    Agrega o actualiza un 'Área de texto y medios' en la sección indicada.
    Si ya existe uno pero con texto diferente, lo edita para actualizarlo.
    """
    if not titulo or not texto:
        return

    print(f"\n➕ Iniciando adición de 'Área de texto y medios' en Semana {semana_numero}...")

    # Expandir la sección antes de cualquier interacción
    _expandir_seccion(page, semana_numero)

    seccion = page.locator(f'li.section.main[data-number="{semana_numero}"]')

    # Validar si el recurso ya existe
    actividad_existente = seccion.locator('.modtype_label').first
    if actividad_existente.count() > 0:
        # Leer el texto actual del label desde Moodle usando múltiples selectores de respaldo
        texto_actual = actividad_existente.evaluate('''el => {
            const contenido = el.querySelector(".no-overflow, .contentafterlink, .activityname, p");
            return contenido ? contenido.innerText.trim() : el.innerText.trim();
        }''')

        texto_esperado_limpio = texto.strip()

        if texto_actual.strip() == texto_esperado_limpio:
            print(f"⏭️  Área de texto ya es correcta en Semana {semana_numero}. Omitiendo...")
            return

        print(f"♻️  TEXTO INCORRECTO en Semana {semana_numero}.")
        print(f"   Actual  : '{texto_actual[:80]}...' " if len(texto_actual) > 80 else f"   Actual  : '{texto_actual}'")
        print(f"   Esperado: '{texto_esperado_limpio[:80]}...'" if len(texto_esperado_limpio) > 80 else f"   Esperado: '{texto_esperado_limpio}'")
        print(f"   → Editando...")

        # Extraer el cmid desde el id del <li> padre: id="module-CMID"
        li_id = actividad_existente.evaluate('el => el.closest("li.activity") ? el.closest("li.activity").id : ""')
        cmid = li_id.replace("module-", "").strip() if li_id else None

        if not cmid or not cmid.isdigit():
            # Intentar con data-id como respaldo
            cmid = actividad_existente.evaluate('el => el.closest("li.activity") ? el.closest("li.activity").dataset.id || "" : ""')

        if cmid and str(cmid).isdigit():
            base_url = page.url.split("/course/")[0]
            edit_url = f"{base_url}/course/modedit.php?update={cmid}&return=1"
            print(f"   Navegando a formulario de edición (cmid={cmid})...")
            page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            # Actualizar el título (opcional, por si cambió)
            input_titulo = page.locator('input[name="name"]')
            if input_titulo.count() > 0:
                input_titulo.fill(titulo)

            # Actualizar el cuerpo del texto
            iframe_tinymce = page.locator('iframe.tox-edit-area__iframe, iframe[title*="Rich Text"]')
            editor_atto = page.locator('div.editor_atto_content[contenteditable="true"]')
            if iframe_tinymce.count() > 0:
                frame = iframe_tinymce.first.content_frame
                frame.locator('body').evaluate(f'el => el.innerText = {__import__("json").dumps(texto)}')
            elif editor_atto.count() > 0:
                editor_atto.fill(texto)
            else:
                import json as _json
                textarea = page.locator('textarea[name="introeditor[text]"]')
                textarea.evaluate(f'(el) => el.value = {_json.dumps(texto)}')

            page.wait_for_timeout(2000)
            boton_guardar = page.locator('input[name="submitbutton2"]')
            boton_guardar.evaluate('el => el.scrollIntoView({block:"center"})')
            page.wait_for_timeout(1000)
            with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
                boton_guardar.click()
            page.wait_for_selector(f'li.section.main[data-number="{semana_numero}"]', timeout=60000)
            print(f"✅ Área de texto corregida en Semana {semana_numero}.")
            return
        else:
            print(f"⚠️  No se pudo obtener el cmid del label en Semana {semana_numero}. Omitiendo edición.")
            return


    # Usar JS para hacer clic en el botón Añadir (evita el problema de visibilidad)
    boton_add = seccion.locator(f'button[data-action="open-chooser"][data-sectionnum="{semana_numero}"]').last
    print("🖱️  Abriendo el selector de actividades...")
    boton_add.evaluate('el => { el.scrollIntoView({block: "center"}); el.click(); }')

    # Esperamos al modal
    page.wait_for_selector('.modal-dialog, .moodle-dialogue-base:not(.moodle-dialogue-exception)', state="visible", timeout=25000)

    opcion_label = page.locator('div[data-internal="label"]').first
    opcion_label.wait_for(state="visible", timeout=25000)

    print("📄 Seleccionando 'Área de texto y medios'...")
    opcion_label.click()

    page.wait_for_load_state("domcontentloaded")

    print("✍️  Llenando los datos del recurso...")
    input_titulo = page.locator('input[name="name"]')
    input_titulo.wait_for(timeout=25000)
    input_titulo.fill(titulo)

    page.wait_for_timeout(3000)

    iframe_tinymce = page.locator('iframe.tox-edit-area__iframe, iframe[title*="Rich Text"]')
    editor_atto = page.locator('div.editor_atto_content[contenteditable="true"]')

    if iframe_tinymce.count() > 0:
        frame = iframe_tinymce.first.content_frame
        frame.locator('body').fill(texto)
    elif editor_atto.count() > 0:
        editor_atto.fill(texto)
    else:
        import json
        textarea = page.locator('textarea[name="introeditor[text]"]')
        textarea.evaluate(f'(el) => el.value = {json.dumps(texto)}')

    print("💾 Guardando cambios y regresando al curso...")
    boton_guardar = page.locator('input[name="submitbutton2"]')
    boton_guardar.evaluate('el => { el.scrollIntoView({block: "center"}); }')
    page.wait_for_timeout(500)
    with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
        boton_guardar.click()

    page.wait_for_selector(f'li.section.main[data-number="{semana_numero}"]', timeout=60000)
    print(f"✅ Recurso '{titulo}' añadido con éxito en la Semana {semana_numero}.")


def agregar_carpetas_semana(page: Page, semana_numero: int, curso_url: str):
    """
    Agrega las 3 carpetas estándar a la semana indicada con sus respectivas descripciones.
    """
    carpetas_data = [
        {
            "nombre": "Desarrollo de clase",
            "buscar": "desarrollo",
            "descripcion": "En esta carpeta se agruparán los archivos y materiales principales para el desarrollo de la sesión de clases."
        },
        {
            "nombre": "Análisis de competencia",
            "buscar": "nalisis",
            "descripcion": "Aquí se depositarán los recursos orientados al análisis, investigación y fortalecimiento de las competencias."
        },
        {
            "nombre": "Evaluación de sesión",
            "buscar": "valuaci",
            "descripcion": "Espacio destinado para los instrumentos, rúbricas y actividades de evaluación de la sesión actual."
        }
    ]

    print(f"\n📁 Iniciando adición de carpetas estándar en Semana {semana_numero}...")

    # Expandir la sección antes de interactuar
    _expandir_seccion(page, semana_numero)

    seccion = page.locator(f'li.section.main[data-number="{semana_numero}"]')

    for carpeta in carpetas_data:
        try:
            nombre = carpeta["nombre"]
            descripcion = carpeta["descripcion"]

            # Verificar si la carpeta ya existe (case-insensitive)
            actividad_existente = seccion.locator(f'[data-activityname*="{carpeta["buscar"]}" i]')
            if actividad_existente.count() == 0:
                actividad_existente = seccion.locator(f'a.aalink:has-text("{nombre}")')

            if actividad_existente.count() > 0:
                print(f"⏭️  La carpeta '{nombre}' ya existe en la Semana {semana_numero}. Omitiendo...")
                continue

            print(f"🖱️  Abriendo el selector para agregar '{nombre}'...")
            boton_add = seccion.locator(f'button[data-action="open-chooser"][data-sectionnum="{semana_numero}"]').last

            # Usar JS para scroll + click (evita el error de elemento no visible)
            boton_add.evaluate('el => { el.scrollIntoView({behavior: "instant", block: "center"}); el.click(); }')
            page.wait_for_timeout(1500)

            # Esperar al modal
            page.wait_for_selector('.modal-dialog, .moodle-dialogue-base:not(.moodle-dialogue-exception)', state="visible", timeout=25000)

            # Seleccionar 'Carpeta' (folder)
            opcion_folder = page.locator('div[data-internal="folder"]').first
            opcion_folder.wait_for(state="visible", timeout=25000)
            opcion_folder.click()

            # Esperar el formulario
            page.wait_for_load_state("domcontentloaded")

            input_titulo = page.locator('input[name="name"]')
            input_titulo.wait_for(timeout=25000)

            print(f"✍️  Nombrando la carpeta y añadiendo descripción...")
            input_titulo.fill(nombre)

            # Tiempo para que Moodle dibuje el editor
            page.wait_for_timeout(4000)

            iframe_tinymce = page.locator('iframe.tox-edit-area__iframe, iframe[title*="Rich Text"]')
            editor_atto = page.locator('div.editor_atto_content[contenteditable="true"]')

            if iframe_tinymce.count() > 0:
                frame = iframe_tinymce.first.content_frame
                frame.locator('body').fill(descripcion)
            elif editor_atto.count() > 0:
                editor_atto.fill(descripcion)
            else:
                import json as _json
                textarea = page.locator('textarea[name="introeditor[text]"]')
                textarea.evaluate(f'(el) => el.value = {_json.dumps(descripcion)}')

            # Marcar "Muestra la descripción en la página del curso"
            checkbox_show = page.locator('input[type="checkbox"][name="showdescription"]')
            if checkbox_show.count() > 0:
                checkbox_show.evaluate('el => { el.scrollIntoView({block: "center"}); el.checked = true; }')

            print(f"💾 Guardando carpeta '{nombre}'...")
            page.wait_for_timeout(2000)

            boton_guardar = page.locator('input[name="submitbutton2"]')
            boton_guardar.evaluate('el => { el.scrollIntoView({behavior: "instant", block: "center"}); }')
            page.wait_for_timeout(2000)
            with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
                boton_guardar.click()

            page.wait_for_selector(f'li.section.main[data-number="{semana_numero}"]', timeout=60000)
            # Re-expandir después de regresar al curso (Moodle puede colapsar la sección de nuevo)
            _expandir_seccion(page, semana_numero)
            seccion = page.locator(f'li.section.main[data-number="{semana_numero}"]')
            print(f"✅ Carpeta '{nombre}' añadida con éxito.")

        except Exception as e:
            print(f"⚠️ Error al crear la carpeta '{carpeta['nombre']}' en Semana {semana_numero}: {str(e)}")
            print("🔄 Recargando el curso para continuar con la siguiente carpeta...")
            page.goto(curso_url)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(3000)
            _expandir_seccion(page, semana_numero)
            seccion = page.locator(f'li.section.main[data-number="{semana_numero}"]')


def subir_archivos_a_carpetas(page: Page, semana_numero: int, archivos_json: dict, curso_url: str = None):
    """
    Lee un JSON con rutas de archivo por carpeta y sube cada archivo a su carpeta correspondiente.
    Soporta múltiples archivos por carpeta usando una lista.
    JSON esperado: {"desarrollo": ["/ruta/a.pdf", "/ruta/b.pdf"], "analisis": "/ruta/c.pdf"}
    """
    import os

    if not archivos_json:
        return

    # Mapa: clave del JSON → (texto parcial para buscar en data-activityname, label para log)
    carpetas_map = {
        "desarrollo": ("esarrollo",  "Desarrollo de clase"),
        "analisis":   ("nalisis",    "Análisis de competencia"),
        "evaluacion": ("valuaci",    "Evaluación de sesión"),
    }

    for clave, rutas in archivos_json.items():
        if clave not in carpetas_map:
            print(f"⚠️  Clave desconocida en JSON: '{clave}'. Omitiendo.")
            continue

        buscar, label = carpetas_map[clave]

        # Normalizamos a lista por si pasaron un string (un solo archivo)
        if isinstance(rutas, str):
            rutas_lista = [rutas]
        elif isinstance(rutas, list):
            rutas_lista = rutas
        else:
            continue

        archivos_a_subir = []
        for r in rutas_lista:
            if r and os.path.isfile(r):
                archivos_a_subir.append(r)
            else:
                print(f"⚠️  Ruta inválida para '{label}': '{r}'. Omitiendo.")

        if not archivos_a_subir:
            continue

        print(f"\n📤 Procesando archivos para '{label}' (Semana {semana_numero})...")

        _expandir_seccion(page, semana_numero)
        seccion = page.locator(f'li.section.main[data-number="{semana_numero}"]')

        # Buscamos el enlace usando selector CSS case-insensitive o por el texto como respaldo
        enlace = seccion.locator(f'[data-activityname*="{buscar}" i] a.aalink').first
        if enlace.count() == 0:
            enlace = seccion.locator(f'a.aalink:has-text("{label}")').first
            if enlace.count() == 0:
                print(f"❌ No se encontró la carpeta '{label}' en la Semana {semana_numero}. ¿Ya fue creada?")
                continue

        href_view = enlace.get_attribute("href")
        if not href_view or "id=" not in href_view:
            print(f"❌ No se pudo obtener el enlace de '{label}'.")
            continue

        module_id = href_view.split("id=")[-1].split("&")[0]
        base_url = page.url.split("/course/")[0]
        view_url = f"{base_url}/mod/folder/view.php?id={module_id}"

        page.goto(view_url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        archivos_faltantes = []
        for ruta_archivo in archivos_a_subir:
            nombre_archivo = os.path.basename(ruta_archivo)
            # Anti-duplicado: si el archivo ya aparece en la vista, lo omitimos
            if page.locator(f'text="{nombre_archivo}"').count() > 0:
                print(f"⏭️  '{nombre_archivo}' ya existe en '{label}'. Omitiendo.")
            else:
                archivos_faltantes.append((ruta_archivo, nombre_archivo))

        if not archivos_faltantes:
            if curso_url:
                page.goto(curso_url, timeout=60000, wait_until="domcontentloaded")
            continue

        # Hacemos clic en "Editar" para abrir el gestor de archivos
        boton_editar = page.locator('a[href*="edit=1"], a:has-text("Editar"), button:has-text("Editar")').first
        boton_editar.wait_for(state="visible", timeout=10000)
        boton_editar.click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        page.wait_for_selector('.fp-btn-add, .filemanager .fp-content', timeout=20000)

        # Iteramos sobre los archivos que nos falta subir en esta carpeta
        for ruta_archivo, nombre_archivo in archivos_faltantes:
            print(f"📎 Inyectando archivo: {nombre_archivo}...")
            page.wait_for_timeout(1000)

            boton_add_file = page.locator('.fp-btn-add').first
            boton_add_file.scroll_into_view_if_needed()
            boton_add_file.click()

            page.wait_for_selector('.fp-repo-area, .filepicker-tabs', state="visible", timeout=15000)
            page.wait_for_timeout(1000)

            opcion_subir = page.locator('.fp-repo-area a:has-text("Subir un archivo")').first
            if opcion_subir.count() == 0:
                opcion_subir = page.locator('a:has-text("Subir un archivo")').first
            opcion_subir.click()
            page.wait_for_timeout(1000)

            boton_seleccionar = page.locator('input[name="repo_upload_file"]').first
            boton_seleccionar.set_input_files(ruta_archivo)
            page.wait_for_timeout(1000)

            print(f"⬆️  Subiendo {nombre_archivo}...")
            boton_subir = page.locator('button:has-text("Subir este archivo")').first
            boton_subir.wait_for(timeout=10000)
            boton_subir.click()

            # Esperamos a que el modal de subida desaparezca
            page.wait_for_selector('.fp-repo-area', state="hidden", timeout=30000)
            page.wait_for_timeout(1500)

        boton_guardar = page.locator('input[name="submitbutton2"], input[value="Guardar cambios"]').first
        boton_guardar.scroll_into_view_if_needed()
        with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
            boton_guardar.click()
        print(f"✅ Archivos guardados en '{label}' (Semana {semana_numero}).")

        # Regresamos al curso
        if curso_url:
            page.goto(curso_url, timeout=60000, wait_until="domcontentloaded")
