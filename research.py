"""
Research module: note.com の市場調査
- note.com 公開 API からトレンドデータを取得
- Claude + Web検索で売れる記事の傾向を分析
"""
import requests
import anthropic
from typing import Optional


_NOTE_API = "https://note.com/api/v2"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "ja,en-US;q=0.9",
}


def fetch_trending_notes(per_page: int = 30) -> list[dict]:
    """note.com 公開 API からトレンド記事を取得（失敗時は空リスト）"""
    try:
        resp = requests.get(
            f"{_NOTE_API}/notes",
            params={"context": "trending", "page": 1, "per_page": per_page},
            headers=_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("notes", [])
    except Exception:
        return []


def analyze_notes(notes: list[dict]) -> dict:
    """取得したノートデータから主要指標を抽出"""
    if not notes:
        return {}

    paid = [n for n in notes if n.get("price", 0) > 0]
    prices = [n["price"] for n in paid]

    top_liked = sorted(notes, key=lambda x: x.get("like_count", 0), reverse=True)

    return {
        "sample_size": len(notes),
        "paid_count": len(paid),
        "paid_ratio": f"{len(paid) / len(notes) * 100:.1f}%",
        "avg_price": int(sum(prices) / len(prices)) if prices else 0,
        "price_range": f"{min(prices, default=0)}円〜{max(prices, default=0)}円",
        "paid_titles": [n.get("name", "") for n in paid[:10]],
        "top_liked_titles": [n.get("name", "") for n in top_liked[:5]],
        "trending_titles": [n.get("name", "") for n in notes[:15]],
    }


def research_market(client: anthropic.Anthropic, api_data: Optional[dict] = None) -> str:
    """Claude + Web検索でnote.com の市場インサイトを調査・分析"""
    print("  🔍 Claude + Web検索で市場調査中...")

    api_context = ""
    if api_data:
        titles_str = "、".join(api_data.get("trending_titles", [])[:5])
        api_context = f"""
[note.com APIデータ（参考）]
サンプル数: {api_data['sample_size']}件
有料記事: {api_data['paid_count']}件（{api_data['paid_ratio']}）
平均価格: {api_data['avg_price']}円 / 価格帯: {api_data['price_range']}
トレンド例: {titles_str}
"""

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=4000,
        thinking={"type": "adaptive"},
        tools=[{"type": "web_search_20260209", "name": "web_search"}],
        system="あなたはnoteプラットフォームの市場調査専門家です。Web検索で最新情報を収集し、「実際に売れる有料記事」を書くための実践的なインサイトをまとめてください。",
        messages=[{
            "role": "user",
            "content": f"""noteで売れている有料記事の市場調査をお願いします。{api_context}

以下の観点で詳しく調査・分析してください：

1. **人気ジャンル** — 現在最も売れているカテゴリ（ビジネス、副業、IT、クリエイターなど）
2. **タイトルパターン** — 購買率が高い記事タイトルの傾向と書き方のコツ
3. **価格戦略** — 売れやすい価格帯（100円/500円/1000円/それ以上）と設定のポイント
4. **コンテンツの特徴** — 買いたいと思わせる内容の特徴（ノウハウ/テンプレート/独自分析/体験談）
5. **ターゲット読者** — 実際に購入している読者層とその悩み
6. **成功パターン** — 売上を上げているクリエイターやコンテンツの具体的な事例

実際に売れる記事を書くための、具体的で実践的なインサイトをまとめてください。""",
        }],
    ) as stream:
        message = stream.get_final_message()

    return "\n".join(b.text for b in message.content if b.type == "text")
