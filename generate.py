"""
Generation module: 市場調査をもとに Claude で記事下書きを生成・保存
"""
import re
import json
from datetime import datetime
from pathlib import Path
import anthropic

DRAFTS_DIR = Path("drafts")
DRAFTS_DIR.mkdir(exist_ok=True)


def generate_topic_ideas(client: anthropic.Anthropic, research_report: str) -> list[dict]:
    """市場調査レポートをもとに売れそうな記事アイデアを5件提案"""
    print("  💡 記事トピックを考案中...")

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2000,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": f"以下はnote.comの市場調査レポートです。このデータをもとに記事提案を行ってください。\n\n{research_report}",
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": """市場調査に基づき、「大学職員になりたい人」または「大学職員の仕事内容を知りたい人」に向けた、noteで売れる可能性が高い有料記事のアイデアを5件提案してください。

筆者は現役の大学職員であり、内部情報・実体験・採用試験対策などリアルな情報を提供できる点が強みです。

以下の形式でJSONのみ返してください（他のテキストは不要）：
[
  {
    "title": "記事タイトル（購買意欲を高める魅力的なもの。例：「現役大学職員が教える〇〇」「採用試験倍率◯倍を突破した〇〇」）",
    "topic": "メインテーマ（一言で。例：採用試験対策、面接対策、仕事内容リアル、部署別業務、私立vs国立比較）",
    "target": "ターゲット読者（具体的に。例：大学職員への転職を考えている20〜30代社会人）",
    "price": 推奨価格（整数、円）,
    "reason": "売れると考える理由（60字以内）",
    "outline": ["章タイトル1", "章タイトル2", "章タイトル3", "章タイトル4"]
  }
]""",
        }],
    )

    raw = next((b.text for b in message.content if b.type == "text"), "[]")
    json_match = re.search(r"\[[\s\S]*\]", raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return []


def generate_article(
    client: anthropic.Anthropic,
    topic_idea: dict,
    research_report: str,
) -> str:
    """選択されたトピックで記事本文をストリーミング生成（コンソール表示しながら構築）"""
    title = topic_idea.get("title", "無題")
    target = topic_idea.get("target", "一般読者")
    price = topic_idea.get("price", 500)
    outline = topic_idea.get("outline", [])
    outline_str = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(outline))

    print(f"\n  ✍️  執筆開始: 「{title}」")
    print("  " + "─" * 56)

    parts: list[str] = []

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=[{
            "type": "text",
            "text": (
                "あなたは現役の大学職員であり、noteで有料記事を執筆しています。\n"
                "読者ターゲットは「大学職員になりたい人」「大学職員の仕事内容を知りたい人」です。\n"
                "現場で働くからこそ知っている内部情報・リアルな体験談・具体的な数字を盛り込み、\n"
                "読者が「お金を払う価値がある」と感じる実践的で高品質な日本語記事を書いてください。\n"
                "採用試験対策・面接対策・業務内容・職場環境・キャリアパスなど、\n"
                "就職・転職希望者が本当に知りたいリアルな情報を提供することを意識してください。\n\n"
                f"【市場調査レポート（参考）】\n{research_report}"
            ),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": f"""以下の仕様でnote有料記事を執筆してください。

■ 記事情報
タイトル: {title}
ターゲット読者: {target}
販売価格: {price}円
章構成:
{outline_str}

■ 執筆要件
- 合計3000〜5000文字程度
- マークダウン形式（# ## ### 見出し、箇条書き、**太字** を活用）
- 冒頭300文字程度は無料プレビュー部（読者の共感を得て購買意欲を刺激する内容）
- 「---ここから有料---」という区切り行の後に有料パートを続ける
- 各章に実例・具体的な数字・ステップを含める
- 読者がすぐ行動できる「アクションステップ」を含める
- 読者の悩みに共感し解決策を提示するトーンで書く

記事全文を書いてください。""",
        }],
    ) as stream:
        for chunk in stream.text_stream:
            print(chunk, end="", flush=True)
            parts.append(chunk)

    print("\n  " + "─" * 56)
    return "".join(parts)


def save_draft(topic_idea: dict, article_content: str) -> Path:
    """記事をフロントマター付きマークダウンとして drafts/ に保存"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    title = topic_idea.get("title", "無題")

    # 安全なファイル名（日本語・英数字を保持、記号除去）
    safe_title = re.sub(r"[^\w぀-鿿\s]", "", title)[:28].strip()
    filename = f"{date_str}_{safe_title}.md"
    filepath = DRAFTS_DIR / filename

    frontmatter = (
        f"---\n"
        f"title: {title}\n"
        f"created: {now.strftime('%Y-%m-%d %H:%M')}\n"
        f"topic: {topic_idea.get('topic', '')}\n"
        f"target_audience: {topic_idea.get('target', '')}\n"
        f"price_recommendation: {topic_idea.get('price', 500)}\n"
        f"reason: {topic_idea.get('reason', '')}\n"
        f"status: draft\n"
        f"---\n\n"
    )

    filepath.write_text(frontmatter + article_content, encoding="utf-8")
    return filepath
