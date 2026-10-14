# V6 사용 방법

수정 엑셀과 지정 수정 ZIP을 우선 사용하고 원본 파일은 수정하지 않습니다. 기존 완료 이미지와 옵션은 검증된 소스·메타데이터·출력 해시가 같으면 유지합니다.

```bash
python automation/catalog.py
python automation/validate_catalog.py
python automation/test_v6.py
python automation/test_v5.py
python automation/test_resume.py
```

`--only CODE ...`는 선택 처리, `--finalize-only`는 ZIP·미리보기 갱신입니다. 미완료가 남으면 종료 코드 2와 상세 상태를 기록합니다. 같은 명령으로 재개할 수 있습니다.

V6 배지는 상품명 아래 상단 좌측을 우선하고 우측도 검토합니다. 지름 160px, 프레임 안쪽부터 최소 40px, 하단·프레임·헤더 침범 금지를 유지합니다. 비백색 픽셀 겹침은 순위 계산에만 쓰며 제품 외곽·뚜껑·사진 배경의 일부 겹침을 허용합니다.

브랜드명·제품명·주요 라벨·중요한 특징은 `catalog-important-regions.json`의 원본 SHA256 및 원래 제품 배치에 연결된 영역으로 보호합니다. 새로운 원본이나 배치에는 옛 주석을 적용하지 않습니다. `badge_rules.py`의 원과 사각형 교차 검사가 실제 중요 영역만 검사합니다.

주석이 없는 새 상품에는 Tesseract를 선택적 보조 OCR로 사용합니다. 없거나 작은 글씨·한글·특징 판단이 불확실하면 후보를 `review_required`로 기록합니다. 저수준 렌더러는 후보와 검수 메타데이터를 반환하며, 최종 생산은 `catalog.py`의 검수 승인 절차를 사용하세요.

시각 검수는 `catalog-v6-reviews.json`에 decision=approved, 출력 PNG SHA256, 원본 SHA256, 검수 메모를 기록합니다. 해당 원본과 정확한 출력에 대한 검수 기록이 일치해야 최종 PNG와 ZIP에 포함됩니다. 중요 영역에 닿는 후보는 승인 기록만으로 우회할 수 없습니다. 검수 대기는 제작 오류와 구분하며 옵션·상품 전체 미완료 사유도 유지합니다.

기존 `badge_centers` 수동 좌표와 `v6_product_translation` 위치 조정을 지원합니다. 위치 조정은 원래 프레임 안의 배치 가능 영역으로 제한하며 제품 픽셀 크기·비율·텍스트·프레임을 유지합니다. 현재 IM0005/NC0001에만 적용합니다. 과거 V5의 검증된 정상 디자인은 보존하고 새/수정 V6 후보에 새 기준을 적용합니다.

ZIP은 내용·상태가 이미 최신이면 바이트와 수정 시각을 유지하고, 바뀐 상품만 재생성합니다. CRC와 내부 PNG 바이트를 검증합니다.

[최종 V6 보고서](../output/V6-REPORT.md) · [18개 미리보기](../previews/v6/README.md) · [전체 카탈로그](../previews/catalog/README.md). [V5 보고서](../output/V5-REPORT.md)는 이전 단계 기록입니다.
