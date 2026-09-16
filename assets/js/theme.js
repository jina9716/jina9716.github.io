(function() {
  var toggle = document.getElementById('theme-toggle');
  var prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

  function getStoredTheme() {
    try {
      return localStorage.getItem('theme');
    } catch(e) {
      return null;
    }
  }

  function storeTheme(theme) {
    try {
      localStorage.setItem('theme', theme);
    } catch(e) {}
  }

  function getTheme() {
    var saved = getStoredTheme();
    if (saved) return saved;
    return prefersDark.matches ? 'dark' : 'light';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    storeTheme(theme);
  }

  setTheme(getTheme());

  if (toggle) {
    toggle.addEventListener('click', function() {
      var current = document.documentElement.getAttribute('data-theme');
      setTheme(current === 'dark' ? 'light' : 'dark');
    });
  }

  prefersDark.addEventListener('change', function(e) {
    if (!getStoredTheme()) {
      setTheme(e.matches ? 'dark' : 'light');
    }
  });
})();

// 본문 이미지 클릭 시 확대. <dialog>가 배경과 Escape 닫기를 담당한다
(function() {
  var images = document.querySelectorAll('.prose img');
  if (!images.length) return;

  var dialog = document.createElement('dialog');
  dialog.className = 'lightbox';
  var full = document.createElement('img');
  dialog.appendChild(full);
  document.body.appendChild(dialog);

  images.forEach(function(img) {
    img.addEventListener('click', function() {
      full.src = img.src;
      full.alt = img.alt;
      dialog.showModal();
    });
  });

  dialog.addEventListener('click', function() {
    dialog.close();
  });
})();
