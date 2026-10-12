/* Acceso de administrador: mostrar/ocultar la clave y aviso de campo vacío (la validación es del servidor). */
(function () {
  var form = document.getElementById('form-acceso');
  if (!form) return;
  var campo = document.getElementById('clave');
  var aviso = document.getElementById('error-clave');
  var boton = document.getElementById('ver-clave');
  var vacio = 'Introduce tu clave de acceso';

  function mostrarError(texto) {
    aviso.textContent = texto;
    if (texto) campo.setAttribute('aria-invalid', 'true'); else campo.removeAttribute('aria-invalid');
  }

  if (boton) {
    boton.hidden = false;
    boton.addEventListener('click', function () {
      var visible = campo.type === 'password';
      campo.type = visible ? 'text' : 'password';
      boton.setAttribute('aria-label', visible ? 'Ocultar clave' : 'Mostrar clave');
      boton.querySelector('.ojo-ver').hidden = visible;
      boton.querySelector('.ojo-ocultar').hidden = !visible;
      campo.focus();
    });
  }

  form.addEventListener('submit', function (ev) {
    if (!campo.value.trim()) { ev.preventDefault(); mostrarError(vacio); campo.focus(); }
  });
  campo.addEventListener('input', function () { if (aviso.textContent) mostrarError(''); });
})();
