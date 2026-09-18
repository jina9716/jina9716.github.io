# jina9716.github.io

백엔드 개발자 박진아의 기술 블로그다. Jekyll 로 만들고 GitHub Pages 에 올린다.

<https://jina9716.github.io>

## 로컬 실행

```bash
bundle install
bundle exec jekyll serve
```

## 구조

| 경로 | 내용 |
|---|---|
| `_posts/` | 블로그 글이다. 파일명은 `YYYY-MM-DD-제목.md` 형식을 따른다 |
| `_layouts/`, `_includes/` | 페이지 레이아웃과 본문 컴포넌트다. 컴포넌트 사용법은 `_includes/README.md` 에 적어 두었다 |
| `_sass/` | 스타일이다. 색은 `_sass/_tokens.scss` 의 CSS 변수로 관리하고, 다크를 기본으로 두고 라이트는 `[data-theme="light"]` 로 덮는다 |
| `assets/` | 이미지와 `assets/js/site.js` 가 들어 있다. 테마 토글과 태그 필터, 목차를 이 스크립트가 담당한다 |

## 배포

`main` 에 푸시하면 `.github/workflows/pages.yml` 이 사이트를 빌드해서 GitHub Pages 에 배포한다.
