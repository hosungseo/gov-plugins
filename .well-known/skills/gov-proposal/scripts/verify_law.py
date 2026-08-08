#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_law.py — 인용 법령을 법제처 국가법령정보 DRF API로 실시간 확인한다.

사용법:
    python3 verify_law.py "공무원 제안 규정"            # 법령 검색: 존재·현행여부·시행일자
    python3 verify_law.py "공무원 제안 규정" --jo 7     # 해당 법령 제7조 전문 출력
    python3 verify_law.py "공무원 제안 규정" --list-jo  # 조문 목차만 출력
    python3 verify_law.py "OO 지침" --admrul            # 행정규칙(고시·훈령·예규·지침) 검색

OC 키는 국가법령정보 공동활용 신청 이메일 ID다. 환경변수 LAW_OC로 바꿀 수 있다.
공개 저장소에 올릴 때는 기본값을 제거할 것.
"""
import argparse
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OC = os.environ.get("LAW_OC", "ghtjd10855")
BASE = "https://www.law.go.kr/DRF"
UA = {"User-Agent": "Mozilla/5.0 (proposal-draft law verifier)"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def search_law(name: str):
    q = urllib.parse.quote(name)
    url = f"{BASE}/lawSearch.do?OC={OC}&target=law&type=XML&query={q}"
    root = ET.fromstring(fetch(url))
    if root.findtext("resultCode") not in ("00", None):
        sys.exit(f"[API 오류] {root.findtext('resultMsg')}")
    laws = []
    for law in root.iter("law"):
        laws.append({
            "명": law.findtext("법령명한글", "").strip(),
            "구분": law.findtext("법령구분명", ""),
            "현행": law.findtext("현행연혁코드", ""),
            "소관": law.findtext("소관부처명", ""),
            "공포": law.findtext("공포일자", ""),
            "시행": law.findtext("시행일자", ""),
            "MST": law.findtext("법령일련번호", ""),
        })
    return laws


def fetch_law_xml(mst: str) -> ET.Element:
    url = f"{BASE}/lawService.do?OC={OC}&target=law&MST={mst}&type=XML"
    return ET.fromstring(fetch(url))


def search_admrul(name: str):
    """행정규칙(고시·훈령·예규·지침·기준) 검색 — 제안서가 자주 인용하는 하위규범."""
    q = urllib.parse.quote(name)
    url = f"{BASE}/lawSearch.do?OC={OC}&target=admrul&type=XML&query={q}"
    root = ET.fromstring(fetch(url))
    rules = []
    for r in root.iter("admrul"):
        rules.append({
            "명": r.findtext("행정규칙명", "").strip(),
            "종류": r.findtext("행정규칙종류", ""),
            "소관": r.findtext("소관부처명", ""),
            "발령": r.findtext("발령일자", ""),
            "현행": r.findtext("현행연혁구분", ""),
        })
    return rules


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="법령명 (정확할수록 좋다)")
    ap.add_argument("--jo", help="조문 번호 (예: 7 또는 7의2)")
    ap.add_argument("--list-jo", action="store_true", help="조문 목차만")
    ap.add_argument("--admrul", action="store_true", help="행정규칙(고시·훈령·예규·지침) 검색")
    args = ap.parse_args()

    if args.admrul:
        rules = search_admrul(args.name)
        if not rules:
            print(f"❌ 행정규칙 '{args.name}' — 검색 결과 없음. 명칭을 확인하라.")
            sys.exit(1)
        for r in rules[:8]:
            mark = "✅" if r["현행"] == "현행" else "⚠️"
            print(f"{mark} {r['현행']} | [{r['종류']}] {r['명']} ({r['소관']}, 발령 {r['발령']})")
        return

    laws = search_law(args.name)
    if not laws:
        print(f"❌ '{args.name}' — law.go.kr에서 찾을 수 없음. 법령명을 확인하라.")
        sys.exit(1)

    exact = [l for l in laws if l["명"] == args.name] or laws
    law = exact[0]
    status = "✅ 현행" if law["현행"] == "현행" else f"⚠️ {law['현행']}"
    print(f"{status} | {law['명']} ({law['구분']}, {law['소관']}) | "
          f"공포 {law['공포']} | 시행 {law['시행']}")
    if len(laws) > 1:
        for other in laws[1:4]:
            if other is not law:
                print(f"   참고: {other['명']} ({other['구분']}, 시행 {other['시행']})")

    if not (args.jo or args.list_jo):
        return

    root = fetch_law_xml(law["MST"])
    if args.list_jo:
        for jo in root.iter("조문단위"):
            n, t = jo.findtext("조문번호", "").strip(), jo.findtext("조문제목")
            if n and t:
                print(f"  제{n}조 {t}")
        return

    target = args.jo.strip()
    found = False
    for jo in root.iter("조문단위"):
        if jo.findtext("조문번호", "").strip() == target and jo.findtext("조문제목"):
            found = True
            print(f"\n── 제{target}조({jo.findtext('조문제목')}) 전문 ──")
            # 내용 요소만 순서대로 모은다 (메타데이터 태그 제외)
            parts = []
            for el in jo.iter():
                if el.tag in ("조문내용", "항내용", "호내용", "목내용") and el.text:
                    parts.append(clean(el.text))
            print("\n".join(p for p in parts if p))
    if not found:
        print(f"❌ 제{target}조를 찾을 수 없음 — 조문 번호를 확인하라.")
        sys.exit(1)


if __name__ == "__main__":
    main()
