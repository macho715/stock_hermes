# Stage 2: Alert Engine — 스펙

## 개요
Position Tracker의 상태 변화를 감지하고 사전 정의된 임계값 초과 시 알림을 발송. 읽기 전용, 주문 실행 없음.

## 파일 위치
`src/stock_rtx4060/alert_engine.py`

## 알림 채널 (플러그인 구조)
- `Lark` — Webhook URL 기반 (免费的, 한국 사용자에게普及)
- `Telegram` — Bot API (설정 필요)
- `Email` — SMTP (선택적)
- `Console` — stdout (기본값, 항상 활성화)

## 알림 트리거 조건
| Alert Type | Condition | Priority |
|------------|-----------|----------|
| `STOP_APPROACHING` | distance_to_stop_pct < 3% | CRITICAL |
| `TP_APPROACHING` | distance_to_tp2_pct < 3% | HIGH |
| `POSITION_CLOSED` | any close event | HIGH |
| `NEW_POSITION` | new position opened | MEDIUM |
| `DRAWDOWN_ALERT` | Track-S drawdown > 5% from peak | HIGH |
| `DAILY_SUMMARY` | daily refresh complete | LOW |
| `EXPOSURE_WARNING` | total exposure > 60% of capital | CRITICAL |
| `MODEL_QUALITY_WARNING` | AUC < 0.55 or OOF coverage < 50% | HIGH |

## 데이터 구조

```python
@dataclass
class Alert:
    alert_type: str
    ticker: str | None
    track: str | None
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    message: str
    timestamp_utc: str
    metadata: dict[str, Any]

class AlertChannel(Protocol):
    def send(self, alert: Alert) -> None: ...

class LarkWebhook(AlertChannel):
    webhook_url: str
    def send(self, alert: Alert) -> None: ...

class TelegramBot(AlertChannel):
    bot_token: str
    chat_id: str
    def send(self, alert: Alert) -> None: ...
```

## 설정 파일
`config/alerts.json`:
```json
{
  "lark_webhook_url": "https://open.larksuite.com/...",
  "telegram_bot_token": null,
  "telegram_chat_id": null,
  "email_smtp": null,
  "alert_enabled": true,
  "thresholds": {
    "stop_approaching_pct": 0.03,
    "tp_approaching_pct": 0.03,
    "max_exposure_pct": 0.60,
    "drawdown_alert_pct": 0.05
  }
}
```

## Position Tracker 통합
- `position_tracker.refresh_positions()` → `alert_engine.check_and_alert()`
- AlertEngine은 position_tracker를 관찰하는 독립 컴포넌트
- 설정 기반으로 알림 채널 동적 선택

## CLI 명령
```powershell
python -m stock_rtx4060.alert_engine --config config/alerts.json --portfolio-json reports/recommendations/*.json --watch --interval 300
```

## 검증
1. `python -m py_compile src/stock_rtx4060/alert_engine.py`
2. `pytest tests/test_alert_engine.py -v`
3. Mock 채널로 트리거 확인

## 의존성
- 기존 `position_tracker.py`
- `requests` (Lark/Telegram webhook용, 이미 Flask 의존으로 사용 가능)
- 설정 파일 (`config/alerts.json`)