# V5 실행 방법

수정 엑셀 `화장품 썸네일_수정.xlsx`가 최우선입니다. 지정 8개 상품은 수정 ZIP만 사용하고 새 이미지 누락 시 기존 사진으로 대체하지 않습니다. 엑셀 브랜드 파일명과 정확히 일치하는 루트 PNG도 브랜드 로고 소스로 지원하며 ZIP과 충돌하면 자동 선택하지 않습니다. 정상 옵션은 소스 해시 기반으로 재사용합니다.

```bash
python -m pip install -r automation/requirements.txt
python automation/catalog.py
python automation/validate_catalog.py
python automation/test_v5.py
python automation/test_resume.py
```

미완료가 남으면 catalog.py는 종료 코드 2와 상세 상태를 남깁니다. 같은 명령으로 재개하고 `--only CODE ...`로 선택 재처리할 수 있습니다. `--finalize-only`는 ZIP과 미리보기만 갱신합니다.

배지 수동 중심은 catalog-overrides.json의 badge_centers에 지정합니다. allow_product_translation에 지정된 상품은 원래 배치 영역 안에서 제품 위치를 조정하며 픽셀 크기와 스케일을 유지합니다. 하단 위치, 텍스트 침범, 프레임 여백 40px 미만, 비백색 영역 겹침 2% 초과는 거절합니다. 흰색 제품 부분은 이 자동 기준만으로 충분하지 않아 시각 검수가 필요합니다.

과거 배지 검수는 SHA256이 일치할 때만 인정합니다. 검수 보류 원본은 previews/v5-before/, 완료 처리하지 않은 후보는 previews/v5-candidates/에 보존합니다. 실패한 대표 이미지가 최종 output/이나 품명별 ZIP에 섞이지 않도록 합니다.

원본 해시 보호를 유지하며, 검증된 소스와 출력에 대해서만 기준을 갱신합니다. 최종 수량·누락·추가 검수 결과는 [V5 보고서](../output/V5-REPORT.md), [전체 미리보기](../previews/catalog/README.md), [추가 비교 이미지](../previews/v5-followup/README.md)를 참고하세요.
