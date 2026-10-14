/* Evaluación por pasos: un paso por área. */
(function () {
  var formulario = document.getElementById('cuestionario');
  if (!formulario) return;
  var pasos = Array.prototype.slice.call(document.querySelectorAll('.paso'));
  var preguntas = document.querySelectorAll('fieldset.pregunta');
  var total = preguntas.length, actual = 0;
  var porArea = pasos.length - 1;
  var ant = document.getElementById('anterior'), sig = document.getElementById('siguiente');
  var enviar = document.getElementById('enviar'), aviso = document.getElementById('aviso-paso');
  var barra = document.getElementById('progreso-barra'), texto = document.getElementById('progreso-texto');
  var barraAria = document.getElementById('progreso-aria'), etiqueta = document.getElementById('paso-etiqueta');
  var items = Array.prototype.slice.call(document.querySelectorAll('.item-area'));
  var nombres = pasos.map(function (p) { var h = p.querySelector('h2'); return h ? h.textContent.replace(/^\d+\.\s*/, '').replace('Opcional', '').trim() : ''; });
  document.getElementById('progreso').hidden = false;

  function respondidas(paso) {
    var n = 0, lista = paso == null ? preguntas : pasos[paso].querySelectorAll('fieldset.pregunta');
    Array.prototype.forEach.call(lista, function (p) { if (p.querySelector('input:checked')) n++; });
    return n;
  }
  function pendientes(paso) {
    return Array.prototype.filter.call(pasos[paso].querySelectorAll('fieldset.pregunta'),
      function (p) { return !p.querySelector('input:checked'); });
  }
  function actualizar() {
    var n = respondidas();
    barra.style.width = (100 * n / total) + '%';
    barraAria.setAttribute('aria-valuenow', n);
    texto.innerHTML = '<b>' + (actual < porArea ? 'Área ' + (actual + 1) + ' de ' + porArea + ': ' + nombres[actual] : 'Último paso: impacto (opcional)') +
      '</b> · ' + n + ' de ' + total + ' preguntas respondidas';
    etiqueta.textContent = actual < porArea ? 'Área ' + (actual + 1) + ' de ' + porArea : 'Último paso';
    pasos.forEach(function (p, i) { p.classList.toggle('paso-oculto', i !== actual); });
    items.forEach(function (b, i) {
      var cuenta = b.querySelector('[data-cuenta]');
      if (cuenta) {
        var r = respondidas(i); cuenta.textContent = r + ' de ' + cuenta.getAttribute('data-total');
        b.classList.toggle('completa', r === +cuenta.getAttribute('data-total'));
      }
      if (i === actual) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current');
    });
    ant.hidden = actual === 0;
    sig.hidden = actual === pasos.length - 1;
    enviar.hidden = actual !== pasos.length - 1;
  }
  function ir(destino, desplazar) {
    actual = Math.max(0, Math.min(pasos.length - 1, destino)); aviso.hidden = true; actualizar();
    if (desplazar !== false) window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  function marcarPendientes(lista) {
    preguntas.forEach(function (p) { p.classList.remove('pendiente'); });
    lista.forEach(function (p) { p.classList.add('pendiente'); });
  }
  sig.addEventListener('click', function () {
    var faltan = actual < porArea ? pendientes(actual) : [];
    marcarPendientes(faltan);
    if (faltan.length) {
      aviso.textContent = 'Falta responder ' + faltan.length + ' pregunta(s) de esta área. Si no conoce la respuesta, marque «No sé».';
      aviso.hidden = false; faltan[0].scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }
    ir(actual + 1);
  });
  ant.addEventListener('click', function () { ir(actual - 1); });
  items.forEach(function (b) { b.addEventListener('click', function () { ir(+b.getAttribute('data-ir')); }); });
  formulario.addEventListener('change', function (e) {
    if (e.target.type === 'radio') e.target.closest('fieldset').classList.remove('pendiente');
    actualizar();
  });
  formulario.addEventListener('submit', function (e) {
    for (var i = 0; i < porArea; i++) {
      var faltan = pendientes(i);
      if (faltan.length) {
        e.preventDefault(); ir(i, false); marcarPendientes(faltan);
        aviso.textContent = 'Falta responder ' + faltan.length + ' pregunta(s) en el área ' + (i + 1) + '.';
        aviso.hidden = false; faltan[0].scrollIntoView({ block: 'center' });
        return;
      }
    }
  });
  /* Impacto: «Limpiar» deja una fila sin valor (aparece solo cuando hay una selección). */
  function botonesLimpiar() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-limpiar]'), function (b) {
      var fila = b.closest('.matriz-fila');
      b.hidden = !fila.querySelector('input:checked');
    });
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-limpiar]'), function (b) {
    b.addEventListener('click', function () {
      Array.prototype.forEach.call(b.closest('.matriz-fila').querySelectorAll('input'), function (i) { i.checked = false; });
      botonesLimpiar();
    });
  });
  formulario.addEventListener('change', botonesLimpiar);
  botonesLimpiar();

  /* Con respuestas precargadas se abre el último paso. */
  actual = respondidas() === total ? pasos.length - 1 : 0;
  actualizar();
})();
