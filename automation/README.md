# V5 사용 방법

수정 엑셀 `화장품 썸네일_수정.xlsx`를 우선 적용합니다. 지정 8개 상품은 수정 ZIP만 사용하며 파일이 없으면 기존 이미지로 대체하지 않습니다. 기존 정상 옵션은 소스 해시 기반으로 재사용합니다.

```bash
python -m pip install -r automation/requirements.txt
python automation/catalog.py
python automation/validate_catalog.py
python automation/test_v5.py
python automation/test_resume.py
```

183개 품명 중 누락 자료나 상단 배지 공간 부족이 있으면 종료 코드 2와 상세 상태 파일을 남깁니다. 같은 명령으로 재개할 수 있습니다. `--only CODE ...`로 선택 처리하고 `--finalize-only`로 ZIP·미리보기만 갱신할 수 있습니다.

상품별 배지 수동 위치는 `catalog-overrides.json`의 `badge_centers`에 중심 좌표를 지정하세요. 하단 후보, 텍스트 침범, 프레임 안전 여백 40px 미만 및 제품 겹침 기준 초과는 수동 설정에서도 금지합니다.

일반 상품은 기존 헤더·제품 크기·프레임을 유지하고 원본 소스로 옛 배지 아래 영역을 복원합니다. 배치 보류한 원본은 `previews/v5-before/`에 보존하고 최종 PNG와 ZIP에는 포함하지 않습니다.

기존 보호 해시는 삭제하지 않습니다. 변경된 보호 대표 썸네일의 기존 바이트는 `previews/v5-before/`로 보존하여 검증합니다. 새 보호 기준 추가는 실제 검증된 소스·결과에 대해서만 실시합니다. 과거 badge review는 SHA256이 일치할 때만 인정합니다.

상세 제작 수량, 누락 목록 및 실제 GitHub 반영 여부는 `../output/V5-REPORT.md`를 참고하세요. GitHub에 V5가 반영되지 않았다면 보고서에 명시됩니다.
