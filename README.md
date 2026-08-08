# gov-plugins — 공무원용 에이전트 스킬 카탈로그

한국 공무원 업무용 AI 에이전트 스킬 모음. [Agent Skills](https://agentskills.io) 표준(SKILL.md)을
따르며, 정적 호스팅만으로 [Hermes](https://github.com/NousResearch/hermes-agent) 스킬허브의
**well-known 소스**로 자동 발견된다.

## 사용법 (Hermes)

스킬허브 검색창에 이 카탈로그가 호스팅된 도메인 URL을 입력하면
`/.well-known/skills/index.json`을 읽어 설치 가능한 스킬 목록을 보여준다.

```
hermes skills 검색 → https://<호스팅 도메인> 입력 → 설치
```

Claude Code 등 다른 플랫폼에서는 스킬 폴더를 그대로 복사해도 동작한다
(플랫폼 무관 자산 원칙).

## 수록 스킬

| 스킬 | 설명 |
|------|------|
| gov-proposal | 공무원제안서 생성 (별지 제1호서식 + 제7조 심사 5축 + law.go.kr 검증) |

## 구조

```
.well-known/skills/
├── index.json          # 카탈로그 인덱스 {"skills": [{name, description, files}]}
└── <skill-name>/
    ├── SKILL.md        # Agent Skills 표준 (필수)
    ├── references/     # 지연 로드 레퍼런스
    └── scripts/        # 보조 스크립트
```

새 스킬 추가: 폴더 생성 → `index.json`의 `skills` 배열에 항목 추가(모든 파일을 `files`에 나열).

## 라이선스

MIT
