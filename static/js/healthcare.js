// custom js
/* Healthcare DSS – Custom JavaScript */

// Mobile sidebar toggle
(function () {
  var sidebar   = document.getElementById('mainSidebar');
  var backdrop  = document.getElementById('sidebarBackdrop');
  var hamburger = document.getElementById('sidebarToggle');
  if (!sidebar) return;
  function openSidebar()  { sidebar.classList.add('open');  if (backdrop) backdrop.classList.add('show'); document.body.style.overflow='hidden'; }
  function closeSidebar() { sidebar.classList.remove('open'); if (backdrop) backdrop.classList.remove('show'); document.body.style.overflow=''; }
  if (hamburger) hamburger.addEventListener('click', openSidebar);
  if (backdrop)  backdrop.addEventListener('click', closeSidebar);
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeSidebar(); });
})();

// Active sidebar link highlighting
(function () {
  var path = window.location.pathname;
  document.querySelectorAll('.sidebar a[href]').forEach(function(a) {
    var href = a.getAttribute('href');
    if (href && href !== '/' && path.startsWith(href)) {
      a.classList.add('active');
    }
  });
})();

// Animate confidence bars after page load
window.addEventListener('load', function() {
  document.querySelectorAll('.confidence-bar[data-width]').forEach(function(bar) {
    var w = bar.getAttribute('data-width');
    setTimeout(function(){ bar.style.width = w + '%'; }, 150);
  });
});

// File upload zone drag-and-drop + click
document.querySelectorAll('.file-upload-zone').forEach(function(zone) {
  var input   = zone.querySelector('input[type="file"]');
  var display = zone.querySelector('.file-name-display');
  if (!input) return;
  zone.addEventListener('click', function(){ input.click(); });
  zone.addEventListener('dragover', function(e){ e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', function(){ zone.classList.remove('drag-over'); });
  zone.addEventListener('drop', function(e){
    e.preventDefault(); zone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      // Cannot assign FileList directly in all browsers; use native input
      if (display) { display.textContent = e.dataTransfer.files[0].name; display.style.display = 'block'; }
    }
  });
  input.addEventListener('change', function(){
    if (input.files.length && display) { display.textContent = input.files[0].name; display.style.display = 'block'; }
  });
});

// AI Run Analysis – show spinner overlay
(function(){
  var form    = document.getElementById('aiAnalysisForm');
  var overlay = document.getElementById('aiSpinnerOverlay');
  if (form && overlay) {
    form.addEventListener('submit', function(){ overlay.classList.add('show'); });
  }
})();

// Auto-dismiss alerts after 6 seconds
document.querySelectorAll('.alert.alert-dismissible').forEach(function(el){
  setTimeout(function(){
    var btn = el.querySelector('.btn-close');
    if (btn) btn.click();
  }, 6000);
});

// Bootstrap tooltips init
if (typeof bootstrap !== 'undefined') {
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function(el){
    new bootstrap.Tooltip(el, { trigger: 'hover' });
  });
}
