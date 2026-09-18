/* 사이트 동작. 의존성 없는 바닐라 JS */
(function () {
  'use strict';

  var THEME_KEY = 'jina-blog-theme';

  function headerOffset() {
    var h = document.querySelector('.site-header');
    return (h ? h.offsetHeight : 68) + 24;
  }

  /* ── 테마 토글 ─────────────────────────────── */
  (function theme() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    var label = document.getElementById('theme-toggle-label');

    function paint(mode) {
      document.documentElement.dataset.theme = mode;
      var isLight = mode === 'light';
      btn.setAttribute('aria-pressed', String(isLight));
      btn.setAttribute('aria-label', isLight ? '어두운 테마로 전환' : '밝은 테마로 전환');
      if (label) label.textContent = isLight ? 'Light' : 'Dark';
    }

    paint(document.documentElement.dataset.theme === 'light' ? 'light' : 'dark');

    btn.addEventListener('click', function () {
      var next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
      paint(next);
      try { localStorage.setItem(THEME_KEY, next); } catch (e) {}
    });
  })();

  /* ── 태그 필터. 해시에 상태를 남겨 새로고침·공유에서 유지된다 ── */
  (function tagFilter() {
    var bar = document.getElementById('tag-filter');
    var list = document.getElementById('post-list');
    if (!bar || !list) return;

    var buttons = Array.prototype.slice.call(bar.querySelectorAll('.filter__btn'));
    var cards = Array.prototype.slice.call(list.querySelectorAll('.post-card'));
    var empty = document.getElementById('filter-empty');

    function apply(tag) {
      var shown = 0;
      cards.forEach(function (card) {
        var tags = (card.getAttribute('data-tags') || '').split('|');
        var hit = !tag || tags.indexOf(tag) !== -1;
        card.hidden = !hit;
        if (hit) shown++;
      });
      buttons.forEach(function (b) {
        b.setAttribute('aria-pressed', String((b.getAttribute('data-tag') || '') === tag));
      });
      if (empty) empty.hidden = shown !== 0;
    }

    function fromHash() {
      var m = /(?:^|[#&])tag=([^&]*)/.exec(location.hash);
      if (!m) return '';
      try { return decodeURIComponent(m[1]); } catch (e) { return ''; }
    }

    buttons.forEach(function (b) {
      b.addEventListener('click', function () {
        var tag = b.getAttribute('data-tag') || '';
        apply(tag);
        var hash = tag ? '#tag=' + encodeURIComponent(tag) : ' ';
        history.replaceState(null, '', tag ? hash : location.pathname);
      });
    });

    window.addEventListener('hashchange', function () { apply(fromHash()); });
    apply(fromHash());
  })();

  /* ── 목차. h2를 읽어 만들고 현재 섹션을 표시한다 ── */
  (function toc() {
    var body = document.getElementById('post-body');
    var nav = document.getElementById('toc-list');
    var box = document.getElementById('toc');
    if (!body || !nav) return;

    var heads = Array.prototype.slice.call(body.querySelectorAll('h2'));
    if (heads.length < 2) { if (box) box.hidden = true; return; }

    /* 좁은 화면에서는 접은 상태로 시작한다 */
    if (box && window.matchMedia('(max-width: 1024px)').matches) box.removeAttribute('open');

    var ul = document.createElement('ul');
    ul.className = 'toc__list-inner';
    ul.style.listStyle = 'none';
    ul.style.margin = '0';
    ul.style.padding = '0';

    var links = [];
    heads.forEach(function (h, i) {
      /* kramdown이 만든 id를 그대로 쓰고, 없을 때만 채워 넣는다 */
      if (!h.id) h.id = 'section-' + (i + 1);
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.className = 'toc__link';
      a.href = '#' + h.id;
      a.textContent = h.textContent.trim();
      a.addEventListener('click', function (e) {
        e.preventDefault();
        var top = h.getBoundingClientRect().top + window.pageYOffset - headerOffset();
        window.scrollTo({ top: top, behavior: 'smooth' });
        history.replaceState(null, '', '#' + h.id);
      });
      li.appendChild(a);
      ul.appendChild(li);
      links.push(a);
    });
    nav.appendChild(ul);

    var visible = new Map();
    function mark(active) {
      links.forEach(function (a, i) {
        a.classList.toggle('is-active', heads[i] === active);
      });
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { visible.set(e.target, e.isIntersecting); });
      var active = null;
      for (var i = 0; i < heads.length; i++) {
        if (visible.get(heads[i])) { active = heads[i]; break; }
      }
      if (!active) {
        var line = headerOffset();
        heads.forEach(function (h) {
          if (h.getBoundingClientRect().top < line) active = h;
        });
      }
      mark(active || heads[0]);
    }, { rootMargin: '-' + headerOffset() + 'px 0px -65% 0px', threshold: 0 });

    heads.forEach(function (h) { io.observe(h); });
  })();

  /* ── 코드블록: 상단 바(파일명·언어)와 복사 버튼 ── */
  (function codeBlocks() {
    var blocks = document.querySelectorAll('.prose div.highlighter-rouge');
    Array.prototype.forEach.call(blocks, function (box) {
      if (box.querySelector('.code-head')) return;

      var lang = '';
      Array.prototype.forEach.call(box.classList, function (c) {
        if (c.indexOf('language-') === 0) lang = c.slice(9);
      });
      /* 파일명은 코드펜스 뒤 {: data-file="..."} 로 지정한다 */
      var file = box.getAttribute('data-file') || box.getAttribute('title') || '';
      if (box.hasAttribute('title')) box.removeAttribute('title');

      var head = document.createElement('div');
      head.className = 'code-head';

      var left = document.createElement('span');
      left.className = 'code-head__file';
      left.textContent = file;

      var right = document.createElement('span');
      right.className = 'code-head__right';

      var copy = document.createElement('button');
      copy.type = 'button';
      copy.className = 'code-copy';
      copy.textContent = 'Copy';
      copy.addEventListener('click', function () {
        var code = box.querySelector('code');
        var text = code ? code.textContent : '';
        var done = function () {
          copy.textContent = 'Copied';
          setTimeout(function () { copy.textContent = 'Copy'; }, 1400);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, function () {});
        }
      });

      var langEl = document.createElement('span');
      langEl.textContent = lang;

      right.appendChild(copy);
      right.appendChild(langEl);
      head.appendChild(left);
      head.appendChild(right);
      box.insertBefore(head, box.firstChild);
    });
  })();

  /* ── 좁은 화면에서 표를 가로 스크롤로 감싼다 ── */
  (function tables() {
    var tables = document.querySelectorAll('.prose table');
    Array.prototype.forEach.call(tables, function (t) {
      if (t.parentElement && t.parentElement.classList.contains('table-scroll')) return;
      var wrap = document.createElement('div');
      wrap.className = 'table-scroll';
      t.parentNode.insertBefore(wrap, t);
      wrap.appendChild(t);
    });
  })();

  /* ── 본문 이미지 확대 ── */
  (function lightbox() {
    var images = document.querySelectorAll('.prose img');
    if (!images.length || typeof HTMLDialogElement === 'undefined') return;

    var dialog = document.createElement('dialog');
    dialog.className = 'lightbox';
    var full = document.createElement('img');
    dialog.appendChild(full);
    document.body.appendChild(dialog);

    Array.prototype.forEach.call(images, function (img) {
      img.addEventListener('click', function () {
        full.src = img.currentSrc || img.src;
        full.alt = img.alt;
        dialog.showModal();
      });
    });
    dialog.addEventListener('click', function () { dialog.close(); });
  })();

  /* ── 홈 마스코트 ───────────────────────────── */
  (function pet() {
    var btn = document.querySelector('.pet');
    if (!btn) return;
    var sprite = btn.querySelector('.pet__sprite');
    var label = btn.querySelector('.pet__label-text');
    /* 진입 상태는 홈의 인라인 스크립트가 이미 정해 뒀다. 여기서는 그 다음 순서만 이어 간다 */
    var states = window.PET_STATES;
    if (!states) return;
    var i = states.findIndex(function (s) { return s[0] === sprite.dataset.state; });

    btn.addEventListener('click', function () {
      i = (i + 1) % states.length;
      sprite.dataset.state = states[i][0];
      label.textContent = states[i][1];
      /* 클래스를 뗐다 붙이는 사이에 리플로우를 한 번 일으켜야 애니메이션이 다시 돈다 */
      label.classList.remove('is-in');
      void label.offsetWidth;
      label.classList.add('is-in');
    });
  })();

})();
