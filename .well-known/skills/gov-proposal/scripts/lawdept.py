#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lawdept.py — 인용 법령의 소관 부처·부서(과 단위)·연락처를 찾아 제출기관 판별과
실시 주체 특정에 쓴다.

동작: ① korea100 lawdept 스냅샷(data/lawdept_snapshot.json, 484개 법령,
2026-07-24 덤프)에서 즉시 조회 → ② 없으면 법제처 DRF API에서 법령 상세를
받아 연락부서를 실시간 추출(--live 기본 허용).

사용법:
    python3 lawdept.py "전자정부법"
    python3 lawdept.py "전자정부법" "공공데이터의 제공 및 이용 활성화에 관한 법률"
    python3 lawdept.py "전자정부법" --no-live    # 스냅샷만 (오프라인)

출처 표기: 스냅샷 히트는 [스냅샷 2026-07-24], 라이브 히트는 [law.go.kr 실시간].
제안서에 인용할 땐 라이브 값을 우선하라 — 부서 개편이 잦다.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OC = os.environ.get("LAW_OC", "ghtjd10855")
BASE = "https://www.law.go.kr/DRF"
UA = {"User-Agent": "Mozilla/5.0 (proposal-draft lawdept)"}
SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "..", "data", "lawdept_snapshot.json")


def load_snapshot():
    try:
        return json.load(open(SNAPSHOT, encoding="utf-8"))
    except FileNotFoundError:
        return None


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def live_lookup(name: str):
    """DRF에서 법령 검색 → 상세 XML의 연락부서 추출."""
    q = urllib.parse.quote(name)
    root = ET.fromstring(fetch(f"{BASE}/lawSearch.do?OC={OC}&target=law&type=XML&query={q}"))
    laws = [l for l in root.iter("law")]
    if not laws:
        return None
    exact = [l for l in laws if (l.findtext("법령명한글") or "").strip() == name] or laws
    law = exact[0]
    mst = law.findtext("법령일련번호", "")
    detail = ET.fromstring(fetch(f"{BASE}/lawService.do?OC={OC}&target=law&MST={mst}&type=XML"))
    depts = []
    for unit in detail.iter("부서단위"):
        d = {
            "부처": (detail.findtext(".//소관부처명") or law.findtext("소관부처명") or "").strip(),
            "부서": (unit.findtext("부서명") or "").strip(),
            "연락처": (unit.findtext("부서연락처") or "").strip(),
        }
        if d["부서"] and d not in depts:
            depts.append(d)
    return {
        "법령명": (law.findtext("법령명한글") or "").strip(),
        "법종": law.findtext("법령구분명", ""),
        "시행일자": law.findtext("시행일자", ""),
        "소관부처": law.findtext("소관부처명", ""),
        "depts": depts,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+", help="법령명 (복수 가능)")
    ap.add_argument("--no-live", action="store_true", help="스냅샷만 사용 (오프라인)")
    args = ap.parse_args()

    snap = load_snapshot()
    by_law = (snap or {}).get("byLaw", {})
    ministries = {}

    for name in args.names:
        hit = by_law.get(name)
        if hit:
            print(f"◆ {name} [{hit.get('법종','')}, 시행 {hit.get('시행일자','')}] — 스냅샷 {snap.get('generated','')}")
            for d in hit.get("depts", []):
                scope = f" ({d['담당범위']})" if d.get("담당범위") else ""
                print(f"   {d.get('부처','')} {d.get('부서','')}{scope} ☎ {d.get('연락처','')}")
                ministries.setdefault(d.get("부처", ""), 0)
                ministries[d.get("부처", "")] += 1
            continue
        if args.no_live:
            print(f"◆ {name} — 스냅샷에 없음 (라이브 조회 생략)")
            continue
        try:
            live = live_lookup(name)
        except Exception as e:  # noqa: BLE001
            print(f"◆ {name} — 라이브 조회 실패: {e}")
            continue
        if not live:
            print(f"◆ {name} — law.go.kr에서 찾을 수 없음. 법령명을 확인하라.")
            continue
        print(f"◆ {live['법령명']} [{live['법종']}, 시행 {live['시행일자']}] — law.go.kr 실시간")
        if live["depts"]:
            for d in live["depts"]:
                print(f"   {d['부처']} {d['부서']} ☎ {d['연락처']}")
                ministries.setdefault(d["부처"], 0)
                ministries[d["부처"]] += 1
        else:
            print(f"   {live['소관부처']} (부서 정보 없음 — 소관부처만 확인)")
            ministries.setdefault(live["소관부처"], 0)
            ministries[live["소관부처"]] += 1

    if len(args.names) > 1 and ministries:
        top = max(ministries, key=ministries.get)
        print(f"\n▶ 제출기관 후보(주된 소관, 영 제5조④ 참고): {top}"
              f" — 부처 분포: {dict(sorted(ministries.items(), key=lambda x: -x[1]))}")
        print("  ※ '주된 내용'의 소관은 인용 빈도가 아니라 제안의 핵심 개선 대상 기준으로 최종 판단하라.")


if __name__ == "__main__":
    main()
