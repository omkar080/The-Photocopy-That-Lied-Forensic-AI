/* ================================================================
   FORENSIC AI — Core Client Interactions
   ================================================================ */

function showToast(message, type) {
  type = type || 'info';
  var container = document.getElementById('toastContainer');
  if (!container) return;
  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function() {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(function() { toast.remove(); }, 300);
  }, 4000);
}

function openZoomModal(src) {
  var modal = document.getElementById('zoomModal');
  var img = document.getElementById('zoomedImage');
  if (modal && img && src) {
    img.src = src;
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeZoomModal() {
  var modal = document.getElementById('zoomModal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

/* --- Dropzone --- */
function initDropzone() {
  var dropzone = document.getElementById('claimDropzone');
  var fileInput = document.getElementById('imageFileInput');
  var preview = document.getElementById('imagePreview');
  var previewImg = document.getElementById('previewImg');
  var fileMeta = document.getElementById('fileMeta');
  var removeBtn = document.getElementById('removeImage');
  if (!dropzone || !fileInput) return;

  function handleFileSelected(file) {
    if (!file) return;
    var validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    if (validTypes.indexOf(file.type) === -1) {
      showToast('Please upload a JPEG or PNG image.', 'error');
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      showToast('File exceeds 25 MB limit.', 'error');
      return;
    }
    var reader = new FileReader();
    reader.onload = function(e) {
      previewImg.src = e.target.result;
      preview.style.display = 'block';
      dropzone.style.display = 'none';
      var sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      fileMeta.textContent = file.name + ' (' + sizeMB + ' MB)';
    };
    reader.readAsDataURL(file);
  }

  dropzone.addEventListener('click', function() { fileInput.click(); });
  dropzone.addEventListener('dragover', function(e) {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', function(e) {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('dragover');
  });
  dropzone.addEventListener('drop', function(e) {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', function() {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  if (removeBtn) {
    removeBtn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      fileInput.value = '';
      preview.style.display = 'none';
      previewImg.src = '';
      fileMeta.textContent = '';
      dropzone.style.display = '';
    });
  }
}

/* --- Evidence Viewer Tabs --- */
function initEvidenceTabs() {
  var tabContainers = document.querySelectorAll('.evidence-viewer');
  tabContainers.forEach(function(container) {
    var tabs = container.querySelectorAll('.evidence-tab');
    var panes = container.querySelectorAll('.evidence-pane');
    tabs.forEach(function(tab) {
      tab.addEventListener('click', function() {
        var target = tab.getAttribute('data-tab');
        tabs.forEach(function(t) { t.classList.remove('active'); });
        panes.forEach(function(p) { p.classList.remove('active'); });
        tab.classList.add('active');
        var pane = container.querySelector('[data-pane="' + target + '"]');
        if (pane) pane.classList.add('active');
      });
    });
  });
}

/* --- Collapsible Sections --- */
function initCollapsibles() {
  var triggers = document.querySelectorAll('.collapsible-trigger');
  triggers.forEach(function(trigger) {
    trigger.addEventListener('click', function() {
      var section = trigger.closest('.collapsible-section');
      if (section) section.classList.toggle('open');
    });
  });
}

/* --- Claims Search/Filter --- */
function initClaimsFilter() {
  var searchInput = document.getElementById('claimsSearch');
  var statusFilter = document.getElementById('statusFilter');
  var resultFilter = document.getElementById('resultFilter');
  if (!searchInput) return;

  function applyFilter() {
    var query = (searchInput.value || '').toLowerCase();
    var statusVal = statusFilter ? statusFilter.value : '';
    var resultVal = resultFilter ? resultFilter.value : '';
    var rows = document.querySelectorAll('.claims-filterable tbody tr');
    rows.forEach(function(row) {
      var text = row.textContent.toLowerCase();
      var matchSearch = !query || text.indexOf(query) !== -1;
      var matchStatus = !statusVal || row.getAttribute('data-status') === statusVal;
      var matchResult = !resultVal || row.getAttribute('data-result') === resultVal;
      row.style.display = (matchSearch && matchStatus && matchResult) ? '' : 'none';
    });
  }

  searchInput.addEventListener('input', applyFilter);
  if (statusFilter) statusFilter.addEventListener('change', applyFilter);
  if (resultFilter) resultFilter.addEventListener('change', applyFilter);
}

/* --- Mobile Menu Toggle --- */
function initMobileMenu() {
  var toggle = document.getElementById('menuToggle');
  var sidebar = document.getElementById('sidebar');
  if (!toggle || !sidebar) return;

  toggle.addEventListener('click', function() {
    sidebar.classList.toggle('mobile-open');
  });

  // Close sidebar on nav click (mobile)
  var navItems = sidebar.querySelectorAll('.nav-item');
  navItems.forEach(function(item) {
    item.addEventListener('click', function() {
      sidebar.classList.remove('mobile-open');
    });
  });
}

/* --- Escape key closes modal --- */
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeZoomModal();
});

/* --- Init all --- */
document.addEventListener('DOMContentLoaded', function() {
  initDropzone();
  initEvidenceTabs();
  initCollapsibles();
  initClaimsFilter();
  initMobileMenu();
});
