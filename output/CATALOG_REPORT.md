# 전체 상품 제작 및 검수 보고서

사용자 확인에 따라 DINSEE 559~560행을 DN0001로 분리하고 EL0001·NF0001의 대표 상품명과 DW0001 로고 지정을 보정했습니다. 원본 Excel은 그대로 유지하며 보정은 `automation/catalog-overrides.json`에 기록했습니다.

## 집계

| 항목 | 수량 |
|---|---:|
| 원본 Excel의 명시적 품명 | 182 |
| 사용자 보정 후 처리 대상 | 183 |
| 브랜드 | 112 |
| 생성·검증된 대표 썸네일 | 175 |
| 생성·검증된 옵션 PNG | 596 |
| 품명별 ZIP | 183 |
| 완전 완료 상품/ZIP | 171 |
| 미완료 상품/부분 ZIP | 12 |

전체 대상은 모두 처리했고, 현재 이용 가능한 정상 매칭 자료는 모두 제작했습니다. **183개 상품이 전부 완성된 것은 아닙니다.** 파일 누락과 빈 Excel 참조가 남아 있습니다. 정상 자료의 렌더링·파일 저장·자동 검수 실패는 없습니다.

## 남은 문제

- 누락된 파일명 참조 6종: 브랜드 SN, YM, HH; 제품 BB0001-16, IC0001-3, IC0001-4. SN 로고는 5개 상품이 공유하므로 영향을 받는 대표 썸네일은 총 8개입니다.
- 대표 미제작: SN0001~SN0005, YM0001, HH0001, BB0001. 사진이 있는 옵션은 이들 상품에서도 제작했습니다.
- IC0001은 옵션 2개가 누락되어 미완료입니다. 다른 정상 옵션과 대표 이미지는 제작했습니다.
- 옵션명은 있지만 옵션 파일 참조가 빈 11행: ET0001 29~33행, YM0001 131~132행, ME0001 140~141행, ET0002 190~191행. 파일을 추측해 채우지 않았습니다.

품명별 ZIP은 모든 183개에 대해 생성했습니다. 171개는 완전한 결과물이며, 12개는 미완료임을 ZIP 내부의 STATUS.json과 검수 목록에 명시했습니다. 대표가 없는 8개 ZIP은 가능한 옵션과 상태 정보만 포함합니다.

## 디자인 및 원본 보존 검수

- 최종 샘플 대표 3개와 옵션 7개는 SHA-256이 작업 전과 동일합니다. 원본 Excel·8개 ZIP·로고·사용자 레퍼런스 파일도 변경하지 않았습니다.
- 생성된 모든 대표 PNG는 1024×1024, 흰색 캔버스, 외곽 여백 12px, 프레임 26px, 같은 색의 160px 원형 1+1 배지를 사용합니다.
- 실제 Excel 매칭 로고·제품 사진의 해시를 검증했습니다. 로고→굵은 상품명→작은 괄호 설명→제품 순서, 텍스트 분리와 비중첩, 최대 비율 맞춤, 프레임 내 영역을 검증했습니다. 중첩 괄호도 순서를 유지하면서 제거합니다.
- 옵션 596개를 원본과 직접 비교해 로고 영역 밖 픽셀이 보존되었고, 오른쪽 상단 실제 분홍색 로고 합성 결과와 일치함을 검증했습니다.
- ZIP 183개의 CRC, 포함 파일 목록, PNG 바이트 및 완료 상태를 검증했습니다.
- 전체 8개 그리드 페이지를 시각적으로 검수했습니다. 비백색 픽셀 점유율로 표시된 배지 12건은 별도로 확인했습니다. 회색·분홍 사진 배경이나 제품 외곽 그림자·모서리의 작은 겹침이 주요 원인이었으며, 제품 전면 글씨·눈·핵심 디테일을 심하게 가리지 않는 위치임을 기록했습니다. 검수 기록은 이미지 해시와 연결되어 있어 파일이 바뀌면 재검수가 필요합니다.

## 산출물 경로

- 개별 대표·옵션: `output/<품명>/<엑셀 썸네일 파일명>.png`, `output/<품명>/options/`
- 품명별 ZIP: `archives/<품명>.zip`
- 전체 목록 및 클릭 가능한 PNG/ZIP: `previews/catalog/README.md`
- 8개 미리보기: `previews/catalog/page-01.png` ~ `page-08.png`
- 완료 목록: `output/catalog-completed.csv`
- 상태 체크포인트: `output/catalog-state.json`
- 오류 로그: `output/catalog-errors.jsonl`
- 집계: `output/catalog-summary.json`
- 자동화: `automation/catalog.py`, `automation/validate_catalog.py` 및 기존 공통 렌더러

개별 PNG와 품명별 ZIP은 일반 Git으로 저장합니다. 가장 큰 개별 ZIP도 약 18MB로 파일 제한보다 작습니다. 대용량 전체 PNG·코드·보고서 묶음은 저장소 외부 `/workspace/catalog-deliverables.zip`로 별도 제공하며 Git에 커밋하지 않습니다. 전체 묶음에는 중복 용량을 줄이기 위해 품명별 ZIP을 다시 넣지 않습니다. 품명별 ZIP은 GitHub archives 폴더에서 개별 다운로드할 수 있습니다. GitHub Release API 접근은 현재 제한되어 있어 Release를 만들었다고 주장하지 않습니다.

## 재시도

누락 파일과 빈 참조를 실제 자료로 보완한 뒤 미완료 상품만 재시도할 수 있습니다. 새 자료는 원본 보호 설정과 검수 입력을 함께 갱신해야 합니다. 다른 상품의 이미지로 대체하지 마세요.

```bash
python automation/catalog.py --retry-failed
python automation/validate_catalog.py
```

완료되지 않은 대상이 있으면 제작 프로그램은 종료 코드 2를 반환합니다. 오류를 숨기거나 183개 전체 완료로 표시하지 않습니다.

## 미완료 상품 목록

| 품명 | 대표 | 제작 옵션 | 남은 문제 |
|---|---|---:|---|
| SN0001 | failed | 2 | brand: SN |
| ET0001 | success | 5 | missing_option_reference (row 29); missing_option_reference (row 30); missing_option_reference (row 31); missing_option_reference (row 32); missing_option_reference (row 33) |
| IC0001 | success | 2 | option: IC0001-3; option: IC0001-4 |
| YM0001 | failed | 2 | missing_option_reference (row 131); missing_option_reference (row 132); brand: YM |
| SN0002 | failed | 2 | brand: SN |
| ME0001 | success | 2 | missing_option_reference (row 140); missing_option_reference (row 141) |
| ET0002 | success | 2 | missing_option_reference (row 190); missing_option_reference (row 191) |
| SN0003 | failed | 2 | brand: SN |
| SN0004 | failed | 2 | brand: SN |
| SN0005 | failed | 2 | brand: SN |
| BB0001 | failed | 15 | thumbnail: BB0001-16 |
| HH0001 | failed | 5 | brand: HH |
