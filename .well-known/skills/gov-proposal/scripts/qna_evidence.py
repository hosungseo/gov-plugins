#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qna_evidence.py — 국민권익위 '민원정책 질의응답' API에서 제안 주제와 관련된
실제 민원 질의를 수집해 ⑧현황과 문제점의 수요 증거로 쓴다.

사용법:
    python3 qna_evidence.py "보도자료"                # 키워드 관련 민원 QnA 목록
    python3 qna_evidence.py "보도자료" --detail 3     # 상위 3건은 질문·답변 전문까지
    python3 qna_evidence.py "제안" --rows 20          # 더 많이

인증키: 환경변수 DATA_GO_KR_KEY, 없으면 스크립트 옆 .env 파일의
DATA_GO_KR_KEY=... 줄을 읽는다 (URL-인코딩된 키 그대로).
API: apis.data.go.kr/1140100/CivilPolicyQnaService (JSON)
  - PolicyQnaList: firstIndex, recordCountPerPage, searchType=1(제목), keyword
  - PolicyQnaItem: faqNo + dutySctnNm (둘 다 필수)
통계 참고: 행안부 공무원 제안 통계(1741000/ProposalByPublicOfficials)는
발급 직후 게이트웨이 동기화 지연으로 Forbidden일 수 있다 — --stats로 시도.
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://apis.data.go.kr/1140100/CivilPolicyQnaService"
STATS = "https://apis.data.go.kr/1741000/ProposalByPublicOfficials/getProposalByPublicOfficials"
UA = {"User-Agent": "Mozilla/5.0 (proposal-draft evidence collector)"}


def load_key() -> str:
    key = os.environ.get("DATA_GO_KR_KEY")
    if key:
        return key
    for envpath in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".env"),
    ):
        if os.path.exists(envpath):
            for line in open(envpath, encoding="utf-8"):
                if line.startswith("DATA_GO_KR_KEY="):
                    return line.split("=", 1)[1].strip()
    sys.exit("인증키 없음: 환경변수 DATA_GO_KR_KEY 또는 프로젝트 루트 .env에 설정하라.")


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        body = r.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        sys.exit(f"[API 비정상 응답] {body[:200]}")


def search(key: str, keyword: str, rows: int) -> dict:
    q = urllib.parse.quote(keyword)
    return get(f"{BASE}/PolicyQnaList?serviceKey={key}&firstIndex=1"
               f"&recordCountPerPage={rows}&searchType=1&keyword={q}")


def item(key: str, faq_no: str, duty: str) -> dict:
    return get(f"{BASE}/PolicyQnaItem?serviceKey={key}&faqNo={faq_no}&dutySctnNm={duty}")


def fmt_date(d: str) -> str:
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) >= 8 else d


def clean_html(s: str) -> str:
    """이중 이스케이프된 HTML 답변을 평문으로."""
    for _ in range(2):
        s = html.unescape(s)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", s)).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword", help="검색 키워드 (제안 주제)")
    ap.add_argument("--rows", type=int, default=10)
    ap.add_argument("--detail", type=int, default=0, metavar="N",
                    help="상위 N건은 질문·답변 전문까지 조회")
    ap.add_argument("--stats", action="store_true", help="공무원 제안 통계 API도 시도")
    args = ap.parse_args()

    key = load_key()
    res = search(key, args.keyword, args.rows)
    if res.get("resultCode") != "S00":
        sys.exit(f"[검색 실패] {res.get('resultCode')} {res.get('resultMessage')}")

    total = res.get("resultCount", "?")
    rows = res.get("resultList", [])
    print(f"◆ '{args.keyword}' 관련 민원정책 QnA: 총 {total}건 (표시 {len(rows)}건)")
    print(f"  ※ 출처: 국민권익위원회 민원정책 질의응답조회서비스, 조회일 기준 실시간")
    for i, r in enumerate(rows, 1):
        print(f"  {i}. [{r.get('ancName','')}] {r.get('title','')} ({fmt_date(r.get('regDate',''))})")

    for i, r in enumerate(rows[: args.detail], 1):
        d = item(key, r["faqNo"], r["dutySctnNm"])
        if d.get("resultCode") != "S00":
            print(f"\n── 상세 {i}: 조회 실패 ({d.get('resultMessage')})")
            continue
        data = d.get("resultData", {})
        print(f"\n── 상세 {i}: {data.get('qnaTitl','')} [{r.get('ancName','')}]")
        q = clean_html(data.get("qstnCntnCl") or "")
        a = clean_html(data.get("ansCntnCl") or "")
        print(f"  [질문] {q[:400]}")
        print(f"  [답변] {a[:400]}")

    if args.stats:
        try:
            body = urllib.request.urlopen(
                urllib.request.Request(f"{STATS}?serviceKey={key}&pageNo=1&numOfRows=5",
                                       headers=UA), timeout=20).read().decode()
            print(f"\n◆ 공무원 제안 통계 API: {body[:300]}")
        except Exception as e:
            print(f"\n◆ 공무원 제안 통계 API: 아직 사용 불가 ({e}) — 키 동기화 후 재시도")


if __name__ == "__main__":
    main()
