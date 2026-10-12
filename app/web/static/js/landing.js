/* Landing: animaciones sutiles; sin JavaScript o con «reducir movimiento» todo se ve de inmediato. */
(function () {
  'use strict';
  var reducir = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hayIO = 'IntersectionObserver' in window;

  var barrer = null;

  /* ---- Cabecera: sombra discreta al desplazarse (no cambia su altura) ---- */
  var cab = document.querySelector('.cabecera');
  if (cab) {
    var pendiente = false;
    var ajustar = function () { pendiente = false; cab.classList.toggle('con-sombra', window.scrollY > 4); if (barrer) barrer(); };
    window.addEventListener('scroll', function () {
      if (!pendiente) { pendiente = true; requestAnimationFrame(ajustar); }
    }, { passive: true });
    ajustar();
  }

  if (reducir) return;

  /* ---- Secciones y tarjetas: se revelan una sola vez al entrar en pantalla ---- */
  if (hayIO) {
    var PASO = 70, MAX_RETRASO = 250;
    var preparar = function (el, i) {
      el.classList.add('rv');
      el.style.setProperty('--d', Math.min(i * PASO, MAX_RETRASO) + 'ms');
    };
    var grupos = [];                
    var unidad = function (sel) {
      Array.prototype.forEach.call(document.querySelectorAll(sel), function (el) { grupos.push({ ancla: el, items: [el] }); });
    };
    var coleccion = function (sel) {
      Array.prototype.forEach.call(document.querySelectorAll(sel), function (cont) {
        grupos.push({ ancla: cont, items: Array.prototype.slice.call(cont.children) });
      });
    };
    unidad('.seccion > h2, .seccion > .intro, .sub-antecedentes');
    coleccion('.pasos');
    unidad('.chips-areas');
    coleccion('.rejilla-3');
    unidad('.desplegable');
    unidad('.faq');
    unidad('.cierre');

    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        var items = e.target.__rv;
        if (!items) return;
        if (!e.isIntersecting) {
          if (e.boundingClientRect.bottom <= 0) {
            observador.unobserve(e.target); e.target.__rv = null;
            items.forEach(function (el) { el.classList.remove('rv'); el.style.removeProperty('--d'); });
          }
          return;
        }
        observador.unobserve(e.target); 
        e.target.__rv = null;
        items.forEach(function (el) {
          el.classList.add('rv-in');
          var limpiar = function () {
            el.classList.remove('rv', 'rv-in'); el.style.removeProperty('--d');
          };
          el.addEventListener('transitionend', function f(ev) {
            if (ev.target !== el || ev.propertyName !== 'opacity') return;
            el.removeEventListener('transitionend', f); limpiar();
          });
          setTimeout(limpiar, 1200);
        });
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });

    var pendientes = [];
    barrer = function () {
      pendientes = pendientes.filter(function (g) {
        if (!g.ancla.__rv) return false;
        if (g.ancla.getBoundingClientRect().bottom > 0) return true;
        observador.unobserve(g.ancla); g.ancla.__rv = null;
        g.items.forEach(function (el) { el.classList.remove('rv'); el.style.removeProperty('--d'); });
        return false;
      });
    };
    grupos.forEach(function (g) {
      pendientes.push(g);
      g.items.forEach(preparar);
      g.ancla.__rv = g.items;
      observador.observe(g.ancla);
    });
  }

  /* ---- Preguntas frecuentes y desplegables: apertura y cierre de ~200 ms ---- */
  var DUR = 200;
  Array.prototype.forEach.call(document.querySelectorAll('.faq details, .desplegable'), function (d) {
    var resumen = d.querySelector('summary');
    if (!resumen || !d.animate) return;
    var anim = null;
    resumen.addEventListener('click', function (ev) {
      ev.preventDefault();
      if (anim) { anim.cancel(); anim = null; d.style.overflow = ''; }
      var inicio = d.offsetHeight, abrir = !d.open, fin;
      d.style.overflow = 'hidden';
      if (abrir) {
        d.classList.remove('cerrando'); d.open = true; fin = d.offsetHeight;
      } else {
        d.classList.add('cerrando'); d.open = false; fin = d.offsetHeight; d.open = true;
      }
      anim = d.animate([{ height: inicio + 'px' }, { height: fin + 'px' }], { duration: DUR, easing: 'ease' });
      anim.onfinish = anim.oncancel = function () {
        anim = null; d.style.overflow = '';
        if (!abrir) { d.open = false; d.classList.remove('cerrando'); }
      };
    });
  });

  /* ---- Ilustración del hero: entrada una sola vez, flotación suave ---- */
  var escena = document.getElementById('escena');
  if (!escena || !hayIO) return;

  escena.classList.add('pre');
  var entrada = new IntersectionObserver(function (entradas) {
    if (!entradas[0].isIntersecting) return;
    escena.classList.add('anima');
    entrada.unobserve(escena); entrada.disconnect();
    setTimeout(function () { escena.classList.add('flotando'); }, 1500);
  }, { threshold: 0.35 });
  entrada.observe(escena);

  /* La flotación se pausa mientras el hero no está en pantalla. */
  new IntersectionObserver(function (entradas) {
    escena.classList.toggle('fuera', !entradas[0].isIntersecting);
  }).observe(escena);
})();
