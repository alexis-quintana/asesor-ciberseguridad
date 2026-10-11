/* Filtros de recomendaciones (mejora progresiva: sin JavaScript se muestran todas). */
(function () {
  var filtros = document.getElementById('filtros');
  var lista = document.getElementById('reco-lista');
  if (!filtros || !lista) return;
  var items = Array.prototype.slice.call(lista.querySelectorAll('.reco'));
  var botones = Array.prototype.slice.call(filtros.querySelectorAll('.pildora'));
  var area = document.getElementById('filtro-area');
  var cuenta = document.getElementById('filtro-cuenta');
  var vacio = document.getElementById('filtro-vacio');
  var prioridad = '';
  filtros.hidden = false;

  function aplicar() {
    var visibles = 0;
    items.forEach(function (li) {
      var ok = (!prioridad || li.getAttribute('data-prioridad') === prioridad) &&
               (!area.value || li.getAttribute('data-area') === area.value);
      li.hidden = !ok; if (ok) visibles++;
    });
    cuenta.textContent = 'Mostrando ' + visibles + ' de ' + items.length;
    vacio.hidden = visibles !== 0;
  }
  botones.forEach(function (b) {
    b.addEventListener('click', function () {
      prioridad = b.getAttribute('data-prioridad');
      botones.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      aplicar();
    });
  });
  area.addEventListener('change', aplicar);
  aplicar();
})();
