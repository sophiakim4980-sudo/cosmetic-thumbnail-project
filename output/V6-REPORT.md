# V6 배지 겹침 허용 최종 보고서

PR #1: https://github.com/sophiakim4980-sudo/cosmetic-thumbnail-project/pull/1

작업 브랜치: `v5-upper-badge-review-20261014`. 기존 PR에 추가 커밋으로 반영하며 main으로 병합하지 않습니다. V5 보고서는 이전 단계 기록으로 보존합니다.

## 최종 수량

- 기존 보류 18개 중 **대표 썸네일 15개 완료**, **추가 시각 검수 3개**: GF0001, HY0002, DF0001.
- 전체 상품 완료 **176/183개**, 미완료 **7개**. 대표 이미지만 완료한 ET0001·ME0001은 옵션 파일 공란 때문에 상품 전체 완료로 처리하지 않았습니다.
- 최종 대표 썸네일 **180개**, 옵션 PNG **596개**, 품명별 ZIP **183개**.
- 배지 상단 좌측 131개, 우측 49개.
- 기존 대표 PNG 165개와 옵션 PNG 596개를 모두 SHA256 비교로 보존 확인했습니다. V6 완료 15개는 제품 픽셀 크기·스케일·브랜드 로고·제목·서브 설명·프레임 색상/두께를 유지했습니다.

## V6 검수 기준

배지 지름 160px, 프레임 안쪽 경계로부터 최소 40px, 상품명 아래 상단 좌우만 사용합니다. 프레임 밖·하단·헤더 겹침은 금지합니다.

배지 영역의 비백색 픽셀 비율은 위치 비교용으로만 사용합니다. 사진 배경·제품 외곽·뚜껑이 조금 겹쳤다는 이유로 실패 처리하지 않습니다. 제품 로고·제품명·주요 라벨·특징은 원본 SHA256과 배치 좌표에 연결된 중요 영역으로 보호합니다. 원형과 실제 중요 영역이 만나는지를 검사하므로 배지 사각형의 빈 모서리만 겹친 경우를 충돌로 오인하지 않습니다.

15개 새 결과는 실제 이미지 시각 검수와 출력 SHA256에 연결된 승인 기록을 통과했습니다. 배경색 픽셀 비율은 실제 제품이 가려진 비율이 아니며 회색 사진 배경에서도 크게 나올 수 있습니다. GF0001·HY0002·DF0001은 중요한 정보를 가리는 후보를 완료 처리하지 않았습니다.

새 상품에 중요 영역 주석이 없으면 OCR을 보조적으로 사용합니다. 작은 글씨·한글·디자인 특징은 OCR만으로 보증하지 않고 `review_required` 상태와 후보 이미지를 남깁니다. 원본/배치 변경 시 이전 주석을 사용하지 않으며, 결과 SHA256과 원본 SHA256이 모두 일치하는 시각 검수 승인만 재사용합니다.

## 18개 상품별 결과

| 품명 | 대표 이미지 | 상품 전체 상태 | 디자인 검수 | 최신 ZIP |
|---|---|---|---|---|
| GF0001 | 추가 검수 | incomplete | 포장 브랜드·주요 라벨과 충돌 | [ZIP](../archives/GF0001.zip) |
| ET0001 | 대표 완료 | incomplete | 위치 유지 | [ZIP](../archives/ET0001.zip) |
| BN0002 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/BN0002.zip) |
| AD0001 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/AD0001.zip) |
| WM0002 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/WM0002.zip) |
| ME0001 | 대표 완료 | incomplete | 위치 유지 | [ZIP](../archives/ME0001.zip) |
| EU0001 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/EU0001.zip) |
| HY0002 | 추가 검수 | incomplete | 파우치 설명·박스 헤드라인과 충돌 | [ZIP](../archives/HY0002.zip) |
| AB0001 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/AB0001.zip) |
| DF0001 | 추가 검수 | incomplete | 마스크 모델 특징·포장 글씨와 충돌 | [ZIP](../archives/DF0001.zip) |
| HY0003 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/HY0003.zip) |
| NC0001 | 대표 완료 | complete | 위치 [81, 0]px 조정, 크기 유지 | [ZIP](../archives/NC0001.zip) |
| DJ0004 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/DJ0004.zip) |
| IF0001 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/IF0001.zip) |
| IM0005 | 대표 완료 | complete | 위치 [58, 0]px 조정, 크기 유지 | [ZIP](../archives/IM0005.zip) |
| DO0001 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/DO0001.zip) |
| RP0001 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/RP0001.zip) |
| SH0001 | 대표 완료 | complete | 위치 유지 | [ZIP](../archives/SH0001.zip) |

IM0005는 +58px, NC0001은 +81px 가로 이동으로 주요 로고를 피했습니다. 크기는 줄이지 않았으며 프레임 안에서 원래 전체 제품 구성을 유지합니다. 나머지 13개 완료 대표는 제품 위치까지 유지했습니다. WM0002는 원본 사진에 있던 배지 위치에 맞춰 중복 배지를 피했습니다.

완료 15개는 새 thumbnail.png를 ZIP에 넣고 PNG 바이트 일치를 검증했습니다. 검수 보류 3개 ZIP은 최신 미완료 사유와 성공한 옵션만 담고, 미승인 대표 후보는 넣지 않았습니다. 지정 18개 ZIP만 갱신했고 나머지 165개 ZIP은 이전 바이트를 유지했습니다.

## 미리보기

18개 상품 미리보기 3페이지: `previews/v6/page-01.png`~`page-03.png`.

15개 수정 전후 비교: `previews/v6/<품명>-comparison.png`.

추가 검수 3개 후보: `previews/v6-review-required/`. 붉은 표시가 있는 후보는 중요 영역과 충돌하여 최종 결과에서 제외됐습니다. 이 후보를 완료 대표 이미지로 사용하지 마세요.

## 나머지 누락·공란 재검사

기존 ZIP 7개, 수정 ZIP 7개 및 수정 엑셀을 다시 확인했습니다. IC0001 원본은 `IC0001-1.png`, `IC0001-2.png`, `IC0001-5.png`만 확인됩니다. **IC0001-3·IC0001-4는 여전히 원본 이미지가 없습니다.** 대표/다른 옵션에서 임의로 자르거나 다른 사진을 지정하지 않았습니다.

옵션 파일 공란 9행은 다음과 같습니다.

| 품명 | 엑셀 행 | 옵션명 | 파일 매칭 |
|---|---:|---|---|
| ET0001 | 29 | 01 Black | 공란 / 확정 매칭 불가 |
| ET0001 | 30 | 02 Brown | 공란 / 확정 매칭 불가 |
| ET0001 | 31 | 03 Gray Brown | 공란 / 확정 매칭 불가 |
| ET0001 | 32 | 04 Volume | 공란 / 확정 매칭 불가 |
| ET0001 | 33 | (NEW) 05 Long Lash | 공란 / 확정 매칭 불가 |
| ME0001 | 138 | (1+1) NutyChoco 45g | 공란 / 확정 매칭 불가 |
| ME0001 | 139 | (1+1) Misutgaru 45g | 공란 / 확정 매칭 불가 |
| ET0002 | 188 | (1+1) 01 Black | 공란 / 확정 매칭 불가 |
| ET0002 | 189 | (1+1) 02 Brown | 공란 / 확정 매칭 불가 |

기존 파일에 같은 색상·맛 이름이 있더라도 단품/1+1 구성 차이가 있고 해당 행의 파일 지정이 없어 정확한 매칭을 확정하지 않았습니다. 임의 대체하지 않고 오류·미완료 목록에 유지했습니다. 상세 실제 ZIP 내부 파일명과 검색 결과는 `output/v6-option-recheck.json`에 있습니다.

## 검증·보존·실행

전체 대표·옵션 PNG, 원본 매칭, 중요 영역, 배지 여백·규격, 183개 ZIP의 CRC와 내부 PNG 바이트 일치를 검증했습니다. V6 회귀 테스트 7개, 기존 V5 회귀 테스트 7개 및 실제 재개 테스트가 통과했습니다. 시각 검수 대기→승인→재개의 실제 동작과 현재 ZIP의 해시·수정 시각 유지도 테스트했습니다.

원본 엑셀·제품 ZIP·브랜드 로고 ZIP·루트 로고 PNG를 수정하거나 삭제하지 않았습니다. 기존 보호 기능도 유지했습니다. 현재 ZIP 내용이 같으면 재생성하지 않아 정상 결과물을 불필요하게 변경하지 않습니다.

```bash
python automation/catalog.py --only GF0001 ET0001 BN0002 AD0001 WM0002 ME0001 EU0001 HY0002 AB0001 DF0001 HY0003 NC0001 DJ0004 IF0001 IM0005 DO0001 RP0001 SH0001
python automation/validate_catalog.py
python automation/test_v6.py
python automation/test_v5.py
python automation/test_resume.py
```

미완료가 남아 catalog.py 종료 코드 2는 예상 상태입니다. 검수 후보는 최종 output/ 및 ZIP에서 제외하고 `review_required`로 구분합니다. 전체 상태와 오류는 `catalog-summary.json`, `catalog-completed.csv`, `catalog-errors.jsonl`에 있으며, 디자인·보존 검증 기록은 `v6-design-review.json`에 있습니다.
