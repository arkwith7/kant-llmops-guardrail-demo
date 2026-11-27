const pptxgen = require('pptxgenjs');
const path = require('path');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'KANT';
pptx.subject = 'Private LLM serving comparison';
pptx.title = 'Ollama와 Kubernetes vLLM 비교';
pptx.lang = 'ko-KR';
pptx.theme = {
  headFontFace: 'NanumBarunGothic',
  bodyFontFace: 'NanumBarunGothic',
  lang: 'ko-KR',
};

const C = {
  ink: '17292D', muted: '53676A', paper: 'F7F9F7', white: 'FFFFFF',
  teal: '087F70', mint: 'DCEFEA', amber: 'C66B35', pale: 'F8E9DB',
  line: 'D5E0DC', navy: '263C46', red: 'AB4D43', light: 'E9EFED',
};
const W = 13.333;
const H = 7.5;
const rect = pptx.ShapeType.rect;
const roundRect = pptx.ShapeType.roundRect;

function box(slide, x, y, w, h, fill, line = fill, radius = false) {
  slide.addShape(radius ? roundRect : rect, {
    x, y, w, h, rectRadius: 0.06,
    line: { color: line, width: 0.7 }, fill: { color: fill },
  });
}

function text(slide, value, x, y, w, h, opts = {}) {
  slide.addText(value, {
    x, y, w, h, fontFace: 'NanumBarunGothic', fontSize: 17,
    color: C.ink, margin: 0, breakLine: false, valign: 'mid',
    ...opts,
  });
}

function header(slide, section, title, page) {
  slide.background = { color: C.paper };
  box(slide, 0, 0, W, 0.12, C.teal);
  text(slide, 'KANT  /  PRIVATE LLM  /  PART 2', 0.58, 0.31, 7.8, 0.21,
    { fontSize: 10, bold: true, color: C.teal });
  text(slide, section, 10.1, 0.31, 2.65, 0.21,
    { fontSize: 10, bold: true, color: C.muted, align: 'right' });
  text(slide, title, 0.58, 0.72, 12.15, 0.58,
    { fontSize: 29, bold: true, color: C.ink });
  box(slide, 0.58, 7.10, 12.17, 0.012, C.line);
  text(slide, 'Ollama vs Kubernetes + vLLM  |  2026.11.27', 0.58, 7.16, 10.6, 0.17,
    { fontSize: 9, color: C.muted });
  text(slide, String(page).padStart(2, '0'), 12.1, 7.14, 0.65, 0.20,
    { fontSize: 10, color: C.teal, align: 'right', bold: true });
}

function label(slide, value, x, y, w, color = C.teal) {
  text(slide, value, x, y, w, 0.25, { fontSize: 11, bold: true, color });
}

function line(slide, value, x, y, w, opts = {}) {
  text(slide, value, x, y, w, opts.h || 0.40, { fontSize: opts.fontSize || 16, ...opts });
}

function card(slide, x, y, w, h, title, body, accent = C.teal) {
  box(slide, x, y, w, h, C.white, C.line);
  box(slide, x, y, 0.06, h, accent);
  text(slide, title, x + 0.24, y + 0.20, w - 0.48, 0.30,
    { fontSize: 17, bold: true, color: accent });
  text(slide, body, x + 0.24, y + 0.65, w - 0.48, h - 0.82,
    { fontSize: 15, color: C.ink, valign: 'top', breakLine: false });
}

{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  box(slide, 0, 0, W, 0.13, C.teal);
  text(slide, 'KANT  /  PRIVATE LLM  /  PART 2', 0.75, 0.55, 9.5, 0.28,
    { fontSize: 13, bold: true, color: 'A9DAD0' });
  text(slide, 'Ollama와\nKubernetes vLLM', 0.75, 1.25, 11.6, 1.55,
    { fontSize: 39, bold: true, color: C.white, breakLine: false });
  text(slide, '성능 · 품질 · 가용성 · 운영 기준으로 비교하기', 0.78, 3.04, 10.9, 0.46,
    { fontSize: 22, color: 'D9E7E4' });
  box(slide, 0.78, 4.12, 11.7, 1.15, '324F56');
  text(slide, '핵심 질문', 1.04, 4.32, 1.15, 0.25,
    { fontSize: 13, color: 'A9DAD0', bold: true });
  text(slide, '간편한 로컬 실행과 다중 사용자 서빙, 무엇을 기준으로 선택할까?',
    1.04, 4.69, 10.95, 0.35, { fontSize: 19, color: C.white, bold: true });
  text(slide, 'RTX 5090 Laptop GPU · WSL2  |  2026.11.27', 0.78, 6.72, 9, 0.25,
    { fontSize: 12, color: 'B9CECA' });
}

{
  const slide = pptx.addSlide();
  header(slide, '구조', '비교 대상은 엔진과 운영 계층을 나눠 본다', 2);
  card(slide, 0.62, 1.67, 5.94, 2.45, 'Ollama · 이 장비의 현재 경로',
    '사용자 / 앱 → Ollama API → 모델 → GPU\n\n로컬 설치와 모델 관리가 간편\n서버 병렬 처리·대기열 설정 가능', C.teal);
  card(slide, 6.77, 1.67, 5.94, 2.45, 'Kubernetes + vLLM · 현재 경로',
    '사용자 / 앱 → 포트 포워딩 → Service\n→ vLLM Pod → 모델 → GPU\n\nvLLM은 추론, Kubernetes는 배포·Pod 관리', C.amber);
  box(slide, 0.62, 4.45, 12.09, 1.38, C.mint);
  text(slide, '공정한 해석', 0.88, 4.68, 2, 0.29,
    { fontSize: 15, bold: true, color: C.teal });
  text(slide, 'Ollama도 Kubernetes에 배포할 수 있고, vLLM도 Docker로 단독 실행할 수 있다.\n엔진 차이와 Kubernetes 운영 효과를 섞어서 단정하지 않는다.',
    0.88, 5.05, 11.45, 0.54, { fontSize: 17 });
}

{
  const slide = pptx.addSlide();
  header(slide, '비교 기준', '선택 기준: 무엇을 얻고 무엇을 부담하는가', 3);
  const rows = [
    ['시작·관리', '설치·모델 교체가 단순', '이미지·GPU 런타임·Pod 설정 필요'],
    ['성능', '가벼운 시작, 병렬·대기열 조정 가능', '연속 배칭·PagedAttention 활용'],
    ['품질', '모델·양자화·프롬프트에 좌우', '동일 조건일 때도 출력 차이 평가'],
    ['가용성', '단일 프로세스면 별도 복구 설계', 'Pod 재생성·준비 상태·배포 관리'],
    ['관측·확장', '운영 도구를 별도로 구성', 'vLLM 지표와 K8s 운영 도구 연결'],
    ['비용·보안', '로컬에서도 접근·모델 관리 필요', '추가 GPU·운영·인증 구성 필요'],
  ];
  const x = [0.65, 2.65, 7.55], widths = [1.95, 4.85, 5.11];
  box(slide, 0.65, 1.57, 12.01, 0.47, C.navy);
  ['기준', 'Ollama', 'Kubernetes + vLLM'].forEach((value, i) =>
    text(slide, value, x[i] + 0.12, 1.65, widths[i] - 0.2, 0.25,
      { fontSize: 14, color: C.white, bold: true }));
  rows.forEach((row, index) => {
    const y = 2.04 + index * 0.61;
    box(slide, 0.65, y, 12.01, 0.60, index % 2 ? C.white : 'EDF3F0', C.line);
    row.forEach((value, col) => text(slide, value, x[col] + 0.12, y + 0.08, widths[col] - 0.22, 0.43,
      { fontSize: col ? 14 : 14, bold: col === 0, color: col === 0 ? C.teal : C.ink }));
  });
  line(slide, '장점은 구성과 부하에 따라 달라진다. 다음 장의 실측 결과와 제약을 함께 확인한다.',
    0.67, 6.03, 12.0, { fontSize: 15, bold: true, color: C.red });
}

{
  const slide = pptx.addSlide();
  header(slide, '성능', '성능은 단일 응답과 동시 부하를 따로 측정', 4);
  card(slide, 0.62, 1.64, 3.85, 2.75, '첫 토큰 지연 · TTFT',
    '요청부터 첫 출력까지\n\n동시 요청별 p50 / p95\n대기열과 입력 처리 영향을 확인', C.teal);
  card(slide, 4.74, 1.64, 3.85, 2.75, '처리량 · 토큰/초',
    '완료된 출력 토큰 ÷ 전체 시간\n\n동시 요청 1 / 2 / 4 / 8\n출력 길이·완료율과 함께 해석', C.amber);
  card(slide, 8.86, 1.64, 3.85, 2.75, '자원 · 안정성',
    'GPU 메모리 / 사용률 / 오류율\n\n모델 로딩과 예열을 분리\n반복 후 분포·최악 지연 기록', C.navy);
  box(slide, 0.62, 4.71, 12.09, 1.15, C.pale);
  text(slide, 'vLLM의 배칭은 다중 요청에서 유리할 가능성이 있지만, 단일 요청부터 항상 빠른 것은 아니다.\nOllama의 병렬 설정과 모델·양자화에 따라 결과가 달라진다.',
    0.89, 4.92, 11.55, 0.72, { fontSize: 16, bold: true });
}

{
  const slide = pptx.addSlide();
  header(slide, '장비 실측', '같은 Qwen3 30B Q4: 부하에 따라 결과가 달라진다', 5);
  label(slide, 'RTX 5090 Laptop · 동일 GGUF · 2K 컨텍스트 · 요청당 최대 64토큰', 0.70, 1.52, 11.6);
  const rows = [
    ['동시 1', '110.9', '26.7', '0.059 / 0.128'],
    ['동시 2', '118.1', '48.9', '0.566 / 0.215'],
    ['동시 4', '118.4', '76.0', '1.647 / 7.212'],
    ['동시 8', '117.4', '177.2', '3.862 / 0.459'],
  ];
  box(slide, 0.65, 1.98, 12.02, 0.55, C.navy);
  const cols = [0.85, 3.05, 5.85, 8.9];
  ['요청', 'Ollama tok/s', 'vLLM tok/s', 'TTFT p95 초: O / V'].forEach((value, index) =>
    text(slide, value, cols[index], 2.12, 2.6, 0.25, { fontSize: 14, color: C.white, bold: true }));
  rows.forEach((row, index) => {
    const y = 2.53 + index * 0.57;
    box(slide, 0.65, y, 12.02, 0.56, index % 2 ? C.white : 'EDF3F0', C.line);
    row.forEach((value, col) => text(slide, value, cols[col], y + 0.12, 2.8, 0.31,
      { fontSize: 16, bold: col === 0, color: col === 0 ? C.teal : C.ink }));
  });
  text(slide, '동시 8에서 vLLM 처리량 1.51배. 동시 4의 vLLM p95 이상치는 재측정 필요.',
    0.69, 5.13, 11.92, 0.39, { fontSize: 16, bold: true, color: C.red });
  text(slide, '동일 질문 반복 · 각 10회 × 동시 수 · GGUF 플러그인 패치 및 eager 모드 · 일반화 금지',
    0.69, 5.68, 11.95, 0.39, { fontSize: 13, color: C.muted });
}

{
  const slide = pptx.addSlide();
  header(slide, '품질', '모델 품질과 서빙 방식은 분리해서 평가', 6);
  card(slide, 0.65, 1.69, 5.86, 2.70, '품질에 영향을 주는 조건',
    '모델 가중치·버전 / 정밀도·양자화\n시스템 프롬프트·채팅 템플릿\n토크나이저 / 컨텍스트 길이\n생성 설정 / 구현·수치 차이', C.teal);
  card(slide, 6.76, 1.69, 5.86, 2.70, '업무 평가셋으로 비교',
    '동일 질문·정답 기준·평가자\n정확성 / 한국어 / 형식 준수\n개인정보·인젝션·금지 작업\n점수와 실패 사례를 함께 기록', C.amber);
  box(slide, 0.65, 4.73, 11.97, 1.16, C.mint);
  text(slide, '동일 가중치로 5개 질문 비교: 4개 응답 일치, 계산 답변은 표현만 다르고 정답.\n소규모 확인일 뿐 업무 품질 우열을 결론내릴 수 없다.',
    0.93, 4.95, 11.39, 0.72, { fontSize: 17, bold: true });
}

{
  const slide = pptx.addSlide();
  header(slide, '가용성', 'Pod 자동 복구와 고가용성은 다르다', 7);
  label(slide, '현재: Minikube · 노트북 1대 · GPU 1장 · Pod 1개', 0.68, 1.59, 11.8);
  card(slide, 0.65, 1.98, 5.88, 2.70, 'Pod 실험 · 각 1회',
    'Qwen3 Pod 생성 → Ready: 159초\nPod 삭제 → 새 Pod Ready: 145초\n이후 실제 추론 응답 확인\nReady 기준, 중단 구간 연속 측정 아님', C.teal);
  card(slide, 6.76, 1.98, 5.88, 2.70, '현재 불가능한 것',
    'GPU·노트북·WSL 장애 자동 우회\n단일 GPU에서 무중단 복제\nRecreate 배포 중 무중단 보장\n포트 포워딩 종료 시 외부 접속', C.red);
  text(slide, '고가용성에는 별도 GPU 노드·복제본·트래픽 경로·장애 시험이 필요하다.',
    0.69, 5.15, 11.91, 0.49, { fontSize: 18, bold: true, color: C.navy });
}

{
  const slide = pptx.addSlide();
  header(slide, '측정 설계', '비교 실험: 같은 조건, GPU는 순차 사용', 8);
  const steps = [
    ['01', '조건 고정', '바이트 동일 GGUF, 2K 컨텍스트, 동일 프롬프트·출력 상한'],
    ['02', '서버 전환', 'vLLM Pod 중지 → Ollama 측정 → Ollama 모델 내림 → vLLM 복구'],
    ['03', '반복 측정', '예열 후 동시 1 / 2 / 4 / 8, 각 동시 수의 10배 요청 기록'],
    ['04', '품질 평가', '지식·계산·SQL·근거·형식 5개 질문, 응답과 기대 기준 보관'],
  ];
  steps.forEach((step, index) => {
    const y = 1.58 + index * 0.94;
    box(slide, 0.65, y, 12.02, 0.80, index % 2 ? C.white : 'EAF2EF', C.line);
    text(slide, step[0], 0.87, y + 0.20, 0.54, 0.32, { fontSize: 17, bold: true, color: C.teal });
    text(slide, step[1], 1.58, y + 0.20, 1.60, 0.32, { fontSize: 16, bold: true });
    text(slide, step[2], 3.10, y + 0.13, 9.22, 0.52, { fontSize: 15 });
  });
  text(slide, '두 서버 각 150/150 성공, usage 기반 토큰 집계. 동시 1의 p95는 10개뿐이다.\n부하·캐시·eager 설정 차이와 동시 4 지연 이상치를 추가 검증해야 한다.',
    0.69, 5.73, 11.95, 0.66, { fontSize: 14, color: C.red, bold: true });
}

{
  const slide = pptx.addSlide();
  header(slide, '선택', '작은 시작은 Ollama, 운영 확장은 요구사항으로 결정', 9);
  card(slide, 0.65, 1.69, 5.86, 2.70, 'Ollama가 잘 맞는 출발점',
    '개인 실습·로컬 프로토타입\n간편한 모델 설치와 교체\n적은 동시 사용자·낮은 운영 부담\n필요하면 운영 환경에 확장', C.teal);
  card(slide, 6.76, 1.69, 5.86, 2.70, 'Kubernetes + vLLM 검토 조건',
    '공유 API·다수 동시 요청\nGPU 자원·배포·관측 표준화\n별도 GPU 노드와 운영 역량 확보\n실측과 업무 품질 기준 충족', C.amber);
  box(slide, 0.65, 4.75, 11.97, 1.12, C.navy);
  text(slide, '추천 순서: 업무 품질 기준 → 실제 부하 측정 → 가용성 목표 → 운영 비용',
    0.93, 5.10, 11.40, 0.38, { fontSize: 19, bold: true, color: C.white });
}

{
  const slide = pptx.addSlide();
  header(slide, '근거', '참고 자료와 이 장비의 확인 범위', 10);
  label(slide, '공식 문서', 0.68, 1.52, 4.5);
  const refs = [
    ['Ollama FAQ · 동시성, 대기열, 로컬 실행', 'https://docs.ollama.com/faq'],
    ['vLLM · PagedAttention, 연속 배칭, API', 'https://docs.vllm.ai/en/stable/'],
    ['Kubernetes · Deployment와 복구·배포', 'https://kubernetes.io/docs/concepts/workloads/controllers/deployment/'],
  ];
  refs.forEach((ref, index) => {
    const y = 1.93 + index * 0.76;
    text(slide, ref[0], 0.70, y, 11.7, 0.25, { fontSize: 15, bold: true });
    text(slide, ref[1], 0.70, y + 0.30, 11.7, 0.24,
      { fontSize: 11, color: C.teal, hyperlink: { url: ref[1] } });
  });
  box(slide, 0.65, 4.50, 12.02, 1.45, C.white, C.line);
  text(slide, '장비 확인', 0.90, 4.75, 2.0, 0.28, { fontSize: 15, bold: true, color: C.teal });
  text(slide, '2026-11-27 · RTX 5090 Laptop 24GB / WSL2 / Minikube / vLLM 0.34.0\n동일 Qwen3 GGUF의 소규모 비교. 상세 조건·원자료: qwen3-비교-실험결과.md',
    0.90, 5.13, 11.35, 0.56, { fontSize: 15 });
}

pptx.writeFile({ fileName: path.join(__dirname, 'Ollama_vs_Kubernetes_vLLM_비교.pptx') });