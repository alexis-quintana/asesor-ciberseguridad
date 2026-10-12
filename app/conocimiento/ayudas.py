# Textos de ayuda del cuestionario.

from __future__ import annotations

# Cuándo marcar cada opción (se muestra en la parte superior del cuestionario).
GUIA_RESPUESTAS = (
    ("Sí", "La práctica existe y se cumple en toda la empresa (todas las personas y equipos)."),
    ("Parcialmente", "Existe solo en algunos equipos, personas o servicios, o está planeada pero no completa."),
    ("No", "La práctica no existe en la empresa."),
    ("No sé", "No conoce la respuesta. Se contará como «No» al calcular el riesgo, "
              "sin afirmar que falte la práctica, y se le indicará cómo verificarla."),
)

AYUDAS = {
    # ------------------------------------------------------------------ cuentas
    "cuentas_individuales": {
        "ejemplo": "Cada persona entra con su propio usuario y contraseña. Es «No» si varias personas comparten un mismo usuario.",
        "verificar": "Pregunte a quien administra los equipos o el correo si existen usuarios compartidos del tipo «caja» o «ventas».",
    },
    "admin_restringido": {
        "ejemplo": "Solo quien lo necesita puede instalar programas o cambiar la configuración del equipo (administrador). Es «No» si todos los empleados son administradores de su computadora.",
        "verificar": "En Windows, abra Configuración > Cuentas y vea si el usuario diario figura como «Administrador».",
    },
    "carpetas_restringidas": {
        "ejemplo": "Cada carpeta compartida (en el servidor o en la nube) solo la abre quien la necesita para trabajar.",
        "verificar": "Revise con quien administra la carpeta compartida quién tiene acceso a las carpetas de contabilidad o clientes.",
    },
    "mfa_publico": {
        "ejemplo": "MFA es el segundo paso al iniciar sesión (código por mensaje o aplicación). Se pregunta por lo que se abre desde Internet: correo web, tienda en línea, banca, sistemas en la nube.",
        "verificar": "Inicie sesión en el correo o sistema desde un equipo nuevo y vea si pide un código adicional.",
    },
    "mfa_cobertura": {
        "ejemplo": "La empresa decidió qué servicios necesitan MFA (correo, banca, sistema de ventas) y lo tienen todos. Es «Parcialmente» si solo algunos lo usan.",
        "verificar": "Haga una lista de los servicios críticos y compruebe en la configuración de cada uno si el MFA está activo.",
    },
    "mfa_contacto_individual": {
        "ejemplo": "Cada persona recibe sus códigos en su propio teléfono o aplicación. Es «No» si varios usuarios dependen del mismo número.",
        "verificar": "Pregunte a quien configuró el MFA a qué teléfono llegan los códigos de cada cuenta.",
    },
    "politica_claves_aplicada": {
        "ejemplo": "Los requisitos de contraseña (largo mínimo, cambios) no solo están escritos: el sistema los exige al crear o cambiar una clave.",
        "verificar": "Intente cambiar una contraseña por «1234» en una cuenta de prueba y vea si el sistema la rechaza.",
    },
    "claves_diferentes": {
        "ejemplo": "Las personas no usan la misma contraseña para el correo, la banca y otros sistemas.",
        "verificar": "Consulte con el personal si usan una misma clave en varios servicios o si usan un gestor de contraseñas.",
    },
    "responsable_accesos": {
        "ejemplo": "Hay una persona concreta que da y quita accesos (por ejemplo cuando alguien entra o sale de la empresa).",
        "verificar": "Pregunte a la gerencia quién autorizó el último alta o baja de un usuario.",
    },
    "acceso_datos_criticos": {
        "ejemplo": "Los datos que no pueden perderse (clientes, facturas, contabilidad) los abre solo el personal autorizado.",
        "verificar": "Identifique dónde están esos datos y pregunte quién puede abrirlos.",
    },
    "permisos_roles": {
        "ejemplo": "Un cajero no ve lo mismo que contabilidad o la gerencia: los permisos dependen del puesto.",
        "verificar": "Revise en el sistema principal si existen perfiles o roles distintos y a quién se asignó cada uno.",
    },
    "accesos_proveedor": {
        "ejemplo": "Si un proveedor de TI atiende los sistemas, hay un acuerdo escrito de qué accesos tiene y qué tareas de seguridad le corresponden.",
        "verificar": "Pida al proveedor (o revise el contrato) qué accesos tiene y qué tareas de seguridad realiza.",
    },
    # ---------------------------------------------------------------- respaldos
    "copia_datos_criticos": {
        "ejemplo": "Se copian periódicamente los archivos sin los cuales el negocio no puede trabajar (clientes, facturas, inventario).",
        "verificar": "Pregunte a quien hace las copias qué archivos incluye y pida ver la última copia realizada.",
    },
    "copia_bases_datos": {
        "ejemplo": "Si usa un sistema con base de datos (ventas, facturación), esa base también se copia, no solo los documentos.",
        "verificar": "Consulte al proveedor del sistema si la base de datos forma parte de las copias.",
    },
    "copia_actualizaciones": {
        "ejemplo": "Las copias incluyen lo que cambió recientemente, no solo una versión antigua de los datos.",
        "verificar": "Compare la fecha del último archivo modificado con la fecha de la copia más reciente.",
    },
    "copia_aplicacion_critica": {
        "ejemplo": "Cada sistema importante (reservas, facturación, tienda en línea) tiene sus datos incluidos en las copias.",
        "verificar": "Haga una lista de sus sistemas importantes y confirme, uno por uno, que están en las copias.",
    },
    "programacion_documentada": {
        "ejemplo": "Existe un calendario escrito: cuándo se copia, quién lo hace y quién comprueba que se hizo.",
        "verificar": "Pregunte si hay un documento o una tarea programada con ese calendario.",
    },
    "frecuencia_conocida": {
        "ejemplo": "La persona responsable sabe si la copia se hace a diario, por semana o por mes.",
        "verificar": "Pregunte a quien hace las copias con qué frecuencia las realiza y revise las fechas de las últimas.",
    },
    "restauracion_probada": {
        "ejemplo": "Alguna vez se recuperó información desde una copia para comprobar que funciona.",
        "verificar": "Pida que se restaure un archivo de prueba desde la copia y anote el resultado.",
    },
    "copia_fuera_sede": {
        "ejemplo": "Hay una copia en otro lugar (nube o disco que se guarda fuera de la oficina) por si hay robo, incendio o inundación.",
        "verificar": "Pregunte dónde se guarda físicamente la copia más reciente.",
    },
    "copia_separada": {
        "ejemplo": "La copia no está solo en el mismo equipo o disco que usa a diario. Si ese equipo falla, la copia no se pierde con él.",
        "verificar": "Compruebe si la copia está en un disco o servicio distinto del equipo que respalda.",
    },
    "copia_cifrada": {
        "ejemplo": "Las copias que salen de la oficina o van a la nube están protegidas con una clave (cifradas) por si alguien las roba.",
        "verificar": "Revise en el programa o servicio de copias si existe la opción de cifrado y si está activada.",
    },
    "alcance_proveedor_copias": {
        "ejemplo": "Si un proveedor hace las copias, usted tiene la lista de qué sistemas respalda y qué responsabilidad asume.",
        "verificar": "Pida al proveedor la lista de sistemas respaldados y las responsabilidades.",
    },
    "plan_recuperacion": {
        "ejemplo": "Existe un procedimiento escrito para volver a trabajar tras una pérdida de datos (qué se recupera primero y quién lo hace).",
        "verificar": "Pregunte a la gerencia si existe un documento con esos pasos.",
    },
    # ------------------------------------------------------------------- correo
    "formacion_general": {
        "ejemplo": "El personal ha recibido alguna capacitación o charla sobre correos falsos y estafas por correo.",
        "verificar": "Pregunte a la gerencia cuándo fue la última capacitación y quiénes asistieron.",
    },
    "formacion_periodica": {
        "ejemplo": "Esa formación se repite cada cierto tiempo (por ejemplo cada año), no fue una sola vez.",
        "verificar": "Revise si hay fechas de más de una capacitación.",
    },
    "formacion_ingreso": {
        "ejemplo": "Quien entra a la empresa recibe indicaciones sobre el correo seguro antes de usar su cuenta.",
        "verificar": "Pregunte al último empleado que ingresó si recibió esas indicaciones.",
    },
    "formacion_phishing": {
        "ejemplo": "Phishing es un correo falso que imita a un banco o proveedor para robar datos. La capacitación incluyó cómo reconocerlo.",
        "verificar": "Pregunte si en la capacitación se mostraron ejemplos de correos falsos.",
    },
    "evidencia_capacitacion": {
        "ejemplo": "Se conserva constancia de cada capacitación (lista de asistentes, fecha, material).",
        "verificar": "Busque la lista de asistencia o el material de la última capacitación.",
    },
    "filtro_spam": {
        "ejemplo": "El correo separa automáticamente los mensajes no deseados (carpeta de spam).",
        "verificar": "Revise si su correo tiene una carpeta de spam que recibe mensajes automáticamente.",
    },
    "filtro_correo_verificado": {
        "ejemplo": "Alguien comprobó que el filtro está activo y funciona, no solo que «debería» estarlo.",
        "verificar": "Pida a quien administra el correo que muestre la configuración del filtro.",
    },
    "adjuntos_desconocidos": {
        "ejemplo": "Antes de abrir un archivo adjunto de alguien que no conoce o que no esperaba, el personal lo verifica.",
        "verificar": "Pregunte al personal qué hace cuando recibe un adjunto inesperado.",
    },
    "enlaces_inesperados": {
        "ejemplo": "El personal desconfía de los enlaces en correos inesperados y comprueba a dónde llevan antes de hacer clic.",
        "verificar": "Pregunte si saben cómo ver el destino de un enlace antes de abrirlo.",
    },
    "urgencias_falsas": {
        "ejemplo": "El personal sabe que un correo que apura («pague hoy o se bloquea su cuenta») puede ser una estafa.",
        "verificar": "Pregunte si han recibido mensajes así y qué hicieron.",
    },
    "adjuntos_rrhh": {
        "ejemplo": "Quien recibe currículos o documentos de postulantes los revisa con cuidado antes de abrirlos.",
        "verificar": "Pregunte a la persona que recibe currículos cómo los revisa. Responda «Sí» solo si existe esa revisión.",
    },
    "revision_post_incidente": {
        "ejemplo": "Si llegó un correo falso o alguien cayó en uno, la empresa lo comentó con todos y reforzó la capacitación.",
        "verificar": "Pregunte si hubo algún incidente de este tipo y qué se hizo después.",
    },
    # -------------------------------------------------------------------- redes
    "cortafuegos": {
        "ejemplo": "El cortafuegos (firewall) filtra lo que entra y sale de la red. Puede ser el del router o un equipo especial.",
        "verificar": "Pregunte a quien instaló la red o al proveedor de Internet si el router tiene el cortafuegos activado.",
    },
    "cortafuegos_verificado": {
        "ejemplo": "Alguien confirmó que el cortafuegos está instalado, activo y con una persona que lo administra.",
        "verificar": "Pida que muestren la pantalla de configuración del cortafuegos y quién la administra.",
    },
    "wifi_invitados_separado": {
        "ejemplo": "Los clientes o visitantes usan una red Wi-Fi distinta de la que usa el personal.",
        "verificar": "Compare las redes Wi-Fi disponibles: ¿la de visitantes es distinta de la de la empresa?",
    },
    "diagrama_red": {
        "ejemplo": "Existe un dibujo o plano actualizado de cómo está conectada la red (router, equipos, impresoras).",
        "verificar": "Pregunte a quien instaló la red si tiene un esquema.",
    },
    "inventario_dispositivos": {
        "ejemplo": "Hay una lista de los equipos conectados: computadoras, servidores, celulares, impresoras y cámaras.",
        "verificar": "Revise si existe una lista y si incluye impresoras y celulares, no solo computadoras.",
    },
    "dispositivo_publico": {
        "ejemplo": "Si algún equipo se puede alcanzar desde Internet (cámaras, router con acceso remoto), tiene protecciones propias. Si no tiene ninguno, marque «Sí».",
        "verificar": "Pregunte al proveedor si hay equipos accesibles desde Internet y qué controles tienen.",
    },
    "aplicacion_publica": {
        "ejemplo": "Si tiene tienda en línea, página con inicio de sesión o sistema en la nube, sus controles de acceso y de datos están revisados. Si no tiene ninguno, marque «Sí».",
        "verificar": "Pregunte a quien desarrolló o administra la tienda o el portal qué controles de seguridad tiene.",
    },
    "parches_equipos": {
        "ejemplo": "Los equipos reciben las actualizaciones de seguridad y alguien comprueba que se instalaron.",
        "verificar": "En Windows, abra Configuración > Windows Update y vea si hay actualizaciones pendientes.",
    },
    "sistema_soportado": {
        "ejemplo": "Los equipos usan versiones del sistema operativo que todavía reciben actualizaciones del fabricante. Un Windows 7 o similar ya no las recibe.",
        "verificar": "Revise la versión del sistema operativo de cada equipo y compare con las fechas de fin de soporte del fabricante.",
    },
    "parches_integrados": {
        "ejemplo": "Impresoras, grabadores de cámaras y otros aparatos conectados también se actualizan, no solo las computadoras.",
        "verificar": "Pregunte si alguien revisa las actualizaciones de impresoras y cámaras.",
    },
    "dispositivos_personales": {
        "ejemplo": "Hay reglas para los celulares o laptops personales que se conectan a la red de la empresa.",
        "verificar": "Pregunte si existe una norma sobre dispositivos personales en la red.",
    },
    "monitoreo_red": {
        "ejemplo": "Alguien revisa lo que ocurre en la red (equipos nuevos, actividad extraña) o hay una herramienta que avisa.",
        "verificar": "Pregunte quién revisa la red y con qué herramienta o frecuencia.",
    },
}


def ayuda(clave):
    return AYUDAS.get(clave, {"ejemplo": "", "verificar": ""})
