# 화장품 썸네일 자동 제작: 전체 카탈로그 및 샘플

원본 Excel과 ZIP을 직접 읽습니다. `catalog.py`는 전체 상품을 처리하고 `generate.py`는 기존 샘플 3개 모드를 유지합니다. 원본 파일의 내용과 파일명을 변경하지 않으며 압축 해제도 필요하지 않습니다.

## 전체 카탈로그 실행·중단 재개

저장소 루트에서 실행하세요. 기본 출력은 저장소의 `output/`, 품명별 ZIP은 `archives/`, 그리드 미리보기는 `previews/catalog/`입니다. 기존 최종 샘플 대표 3개와 옵션 7개는 읽기 검증만 하고 그대로 재사용합니다.

```bash
/workspace/asset-tools-venv/bin/python automation/catalog.py
/workspace/asset-tools-venv/bin/python automation/validate_catalog.py
```

실행 중 상품·이미지별 상태를 원자적으로 저장합니다. 기존 파일의 해시와 소스 지문이 유효하면 재사용합니다. 파일을 임시 PNG로 렌더링하고 검증한 뒤 최종 경로로 교체하므로 중단된 파일을 완료로 인정하지 않습니다. 입력이나 렌더러가 변경되면 영향을 받는 대표 이미지가 재제작될 수 있습니다.

```bash
# 미완료 상품만 재시도; 정상 옵션은 가능한 한 재사용
/workspace/asset-tools-venv/bin/python automation/catalog.py --retry-failed
# 지정된 품명만 재시도
/workspace/asset-tools-venv/bin/python automation/catalog.py --only IC0001 BB0001
# 이미지를 다시 만들지 않고 ZIP/미리보기/상태만 갱신
/workspace/asset-tools-venv/bin/python automation/catalog.py --finalize-only
```

미완료 상품이 남으면 producer 종료 코드는 **2**입니다. 계속 처리된 결과는 보존됩니다. 파일 누락·빈 참조를 성공으로 표시하지 않습니다. Validator 종료 코드 0은 **만들어진 모든 파일이 검증을 통과했다**는 뜻이며, 전체 자료의 누락이 없다는 뜻은 아닙니다. 누락은 `catalog-summary.json`, `catalog-errors.jsonl`과 CSV에 남습니다.

`catalog-overrides.json`에는 사용자가 확인한 DN0001 분리, EL0001·NF0001 대표 상품명, DW 로고 지정을 기록했습니다. 원본 Excel은 변경하지 않습니다. 원본의 명시적 품명은 182개지만 DINSEE 보정 후 실제 처리 그룹은 183개입니다.

`catalog-badge-reviews.json`은 출력 이미지 해시와 연결된 시각 검수 기록입니다. 사진이 여백을 거의 채우는 경우 배지는 사진을 축소하지 않고 캔버스 내의 빈 공간을 검색하며 로고·상품명·설명을 피합니다. 비백색 배경과 실제 제품을 픽셀 점유율만으로 구분할 수 없는 항목은 시각 검수를 기록합니다. 검수 파일은 `catalog-overrides.json`의 사용자 확인 내용과 별도입니다.

`catalog-protected.json`은 원본 자료와 승인된 샘플의 SHA-256 기준입니다. 사용자가 새 원본을 제공한 경우 새 파일을 검토하고 기준을 의도적으로 갱신해야 하며, 검사만 통과시키기 위해 기존 기대 해시를 바꾸지 마세요.

각 품명 ZIP에는 생성된 대표·옵션과 `STATUS.json`이 포함됩니다. 미완료 ZIP은 누락 항목을 명시하며, 대표 사진이 없는 상품은 옵션만 포함할 수 있습니다. 코드가 다른 상품의 이미지를 임의 대체하지 않습니다. 같은 품명의 같은 옵션 참조는 중복 저장하지 않습니다.

전체 묶음은 아래 명령으로 저장소 밖에 생성합니다. 개별 PNG와 품명별 ZIP은 GitHub에서 각각 확인할 수 있으며, 전체 묶음에는 중복 ZIP을 다시 넣지 않습니다.

```bash
/workspace/asset-tools-venv/bin/python automation/package_catalog.py \
  --destination /workspace/catalog-deliverables.zip
```

## 저장된 샘플 확인

이미 제작된 대표 PNG 3개와 옵션 PNG 7개는 저장소의 `output/RL0001/`, `output/LL0001/`, `output/WM0001/`에 있습니다. 미리보기는 `previews/`, 전체 샘플 묶음은 루트의 `sample-deliverables.zip`, 품명별 ZIP과 분석 보고서는 `output/`에 있습니다. 이번 GitHub 저장 작업은 기존 결과물을 바이트 그대로 복사했으며 이미지를 다시 제작하지 않았습니다.

기존 결과물 검증만 실행하려면 저장소 루트에서 다음 명령을 사용하세요.

```bash
/workspace/asset-tools-venv/bin/python automation/validate.py --output output
```

## 필요할 때 다시 제작

### 디자인 2차 수정 실행

대표 이미지만 다시 합성하고 옵션 7개를 그대로 재사용합니다. 옵션 파일 또는 원본 매칭 정보가 없으면 실패하며 다른 이미지로 대체하지 않습니다. 왼쪽 기존/오른쪽 수정 비교와 대표 3장 미리보기를 함께 생성합니다.

```bash
/workspace/asset-tools-venv/bin/python automation/generate.py \
  --output output --previews previews --reuse-options \
  --compare-with previews/before --bundle
/workspace/asset-tools-venv/bin/python automation/validate.py --output output
```

공통 레이아웃 함수는 품명별 고정 좌표 없이 실제 제품 크롭 비율과 텍스트 높이로 배치합니다. 프레임은 외곽 12px 여백을 둔 **26px** 테두리이며 캔버스는 순수 흰색입니다. 로고와 상품명·설명을 하나의 밀집된 그룹으로 배치하고 텍스트 아래 20px부터 하단 970px까지 제품 영역을 확보합니다. 제품은 이 영역에 비율을 유지해 최대 크기로 맞추며, 가로로 넓은 이미지는 상단에 붙이고 세로·세트 이미지는 하단을 채웁니다. 상품명은 기본 52px, 설명은 29px이며 긴 제목은 자연스럽게 줄바꿈합니다.

160px 배지는 제품을 축소하지 않고 실제 비백색 픽셀 점유율이 최소인 여백을 검색합니다. 이번 샘플 3개의 점유율은 모두 0%입니다. 모든 사진의 구성이 달라서 향후 전 상품 제작 시에도 점유율과 미리보기를 검수해야 합니다. 프레임과 배지는 정확히 같은 색을 사용합니다.

`previews/before/`는 수정 전 원본 썸네일이며 비교 생성 기준으로 계속 유지합니다. `previews/*-comparison.png`는 비교용으로 1024 정사각 규격이 아니며, 개별 최종 대표 PNG만 정확히 1024×1024입니다. `previews/thumbnails-overview.png`는 수정 대표 3장을 한 화면에 보여줍니다. `--bundle`은 개별 PNG, 현재 코드, ZIP, 미리보기, 진단을 포함한 최신 전체 ZIP을 만듭니다.

Python 3.12와 DejaVu Sans 글꼴이 있는 Linux 환경에서 검증했습니다.

```bash
cd /workspace/cosmetic-thumbnail-project
python3 -m venv /workspace/asset-tools-venv
/workspace/asset-tools-venv/bin/python -m pip install -r automation/requirements.txt
/workspace/asset-tools-venv/bin/python automation/generate.py \
  --source /workspace/cosmetic-thumbnail-project \
  --output /workspace/cosmetic-thumbnail-output
/workspace/asset-tools-venv/bin/python automation/validate.py --output /workspace/cosmetic-thumbnail-output
```

다른 머신에서는 `--source`, `--output` 경로와 `generate.py`의 `FONT`, `BOLD` 글꼴 경로를 조정하세요. 실행은 비대화형이며 같은 경로에서 재실행할 수 있습니다. 결과 파일은 덮어쓰므로 검수한 결과를 보관하려면 다른 출력 폴더를 지정하세요. 원본과 같은 출력 경로 또는 원본의 상위 경로는 거부합니다.

`generate.py`의 기존 기능과 기본 출력 경로는 유지했습니다. 저장소에 보관한 검수 결과는 재생성 없이 사용할 수 있습니다. 전체 상품 제작은 최종 단계 요청으로 승인되었으며 별도 `catalog.py`를 사용합니다.

## 처리 규칙

- 품명이 비어 있는 행은 직전 상품 그룹에 포함합니다. 브랜드·상품명·로고·대표 이미지 정보는 **같은 그룹 안에서만** 보존하며 옵션 파일의 빈 셀은 임의 채우지 않습니다.
- ZIP 하위 폴더까지 검색하고 한국어 CP949 파일명을 복원합니다. 확장자가 없는 참조는 실제 이미지의 stem과 매칭합니다. 중복 후보와 누락 파일은 추측하지 않고 오류로 기록합니다.
- 브랜드 ZIP과 제품 ZIP의 검색 범위를 분리합니다. 실제로 `RL0001-1.png`라는 서로 다른 파일이 두 영역에 존재하지만 샘플 옵션은 제품 ZIP에서 정확히 선택합니다.
- 대표 이미지는 1024×1024 흰색 PNG이며 26px 컬러 프레임을 사용합니다. 실제 브랜드 로고, 검정 굵은 상품명, 괄호를 제거한 작은 설명, 제품 사진 순으로 배치합니다.
- 외부 흰 여백만 크롭하고 제품 사진 내부의 색·글씨·개수는 유지합니다. 비율을 유지해 축소하며 배경 제거 모델이나 생성형 이미지로 제품을 재구성하지 않습니다.
- 비백색의 채도가 있는 색상에서 프레임 색을 추출합니다. 같은 색으로 160px 원형 1+1 배지를 만들고 제품 영역의 좌우 후보 중 가장 비어 있는 곳을 선택합니다. 배지 때문에 사진을 축소하지 않습니다.
- WM0001 대표 원본은 모델과 제품, 기존 NEW/1+1 배지가 포함된 사진입니다. 기존 배지를 지우지 않고 새 배지를 외부 여백에 추가합니다.
- 옵션 이미지는 원본 픽셀 크기와 비율을 유지하고 실제 분홍색 공통 로고만 오른쪽 위에 합성합니다. 로고 크기와 여백은 동일한 비율을 사용합니다.

## 결과

`output/<품명>/thumbnail.png`, `output/<품명>/options/*.png`, `<품명>.zip`, `<품명>-preview.png`, `all-samples-preview.png`, `analysis.json`, `errors.log`를 생성합니다.

`analysis.json`은 전체 상품 그룹, Excel 행 번호, ZIP 내부 경로, SHA-256, 이미지 매칭, 누락 및 충돌, 샘플 레이아웃을 포함합니다. `errors.log`는 전체 자료의 문제를 담으므로 샘플 성공 시에도 비어 있지 않을 수 있습니다. 샘플 제작 실패 시 프로그램은 종료 코드 1을 반환합니다.

샘플 옵션은 RL0001 2개, LL0001 2개, WM0001 3개입니다. 전체 제작은 아래 catalog 명령으로 실행합니다.
