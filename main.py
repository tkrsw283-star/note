"""
note 記事自動化パイプライン

コマンド:
  python main.py run       調査 → トピック提案 → 記事生成 → 下書き保存
  python main.py research  市場調査のみ実行してレポートを表示
  python main.py list      保存済みの下書き一覧を表示
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import anthropic

from research import fetch_trending_notes, analyze_notes, research_market
from generate import generate_topic_ideas, generate_article, save_draft

load_dotenv()


def _get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY が設定されていません。")
        print("   .env.example を参考に .env ファイルを作成してください。")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


def _do_research(client: anthropic.Anthropic) -> tuple[str, dict | None]:
    """APIデータ取得 + Claude市場調査を実行し (report, api_data) を返す"""
    print("1️⃣  note.com APIからデータを取得中...")
    notes = fetch_trending_notes()
    api_data = analyze_notes(notes) if notes else None

    if api_data:
        print(f"   ✓ {api_data['sample_size']}件取得 / 有料: {api_data['paid_count']}件 / 平均価格: {api_data['avg_price']}円")
    else:
        print("   ℹ️  APIデータなし — Web検索で代替します")

    print("\n2️⃣  市場インサイトを分析中...")
    report = research_market(client, api_data)
    return report, api_data


def cmd_research() -> None:
    """市場調査のみ実行してレポートを表示"""
    client = _get_client()
    print("\n📊 note.com 市場調査\n" + "=" * 60)
    report, _ = _do_research(client)
    print("\n" + "=" * 60)
    print("📋 市場調査レポート")
    print("=" * 60)
    print(report)


def cmd_generate() -> None:
    """全パイプライン: 調査 → トピック選択 → 記事生成 → 保存"""
    client = _get_client()
    print("\n🚀 note 記事生成パイプライン\n" + "=" * 60)

    # ── STEP 1: 市場調査 ───────────────────────────────────────
    print("\n【STEP 1】市場調査")
    print("-" * 40)
    report, _ = _do_research(client)
    print("   ✓ 調査完了")

    # ── STEP 2: トピック提案 ────────────────────────────────────
    print("\n【STEP 2】記事トピック提案")
    print("-" * 40)
    topics = generate_topic_ideas(client, report)

    if not topics:
        print("  ❌ トピック生成に失敗しました。もう一度お試しください。")
        return

    print("\n  提案されたトピック:\n")
    for i, t in enumerate(topics, 1):
        print(f"  {i}. 【{t.get('price', 0)}円】 {t['title']}")
        print(f"     対象: {t.get('target', '—')}")
        print(f"     理由: {t.get('reason', '—')}\n")

    # ── STEP 3: トピック選択（ユーザー入力） ───────────────────
    print("書きたいトピックの番号を入力してください (1–5) [Enter で 1番]: ", end="", flush=True)
    try:
        raw = input().strip()
        idx = int(raw) - 1 if raw else 0
        idx = max(0, min(idx, len(topics) - 1))
    except (ValueError, EOFError):
        idx = 0

    selected = topics[idx]
    print(f"\n  ✓ 選択: 「{selected['title']}」")

    # ── STEP 4: 記事生成 ────────────────────────────────────────
    print("\n【STEP 3】記事執筆")
    print("-" * 40)
    content = generate_article(client, selected, report)

    # ── STEP 5: 保存 ────────────────────────────────────────────
    print("\n【STEP 4】下書き保存")
    print("-" * 40)
    filepath = save_draft(selected, content)
    print(f"  ✓ 保存完了: {filepath}")

    print("\n" + "=" * 60)
    print("✅ 完了！下書きを確認して、投稿するか判断してください。")
    print(f"   📄 ファイル      : {filepath}")
    print(f"   💰 推奨価格      : {selected.get('price', 500)}円")
    print(f"   👥 ターゲット    : {selected.get('target', '—')}")
    print("=" * 60)


def cmd_list() -> None:
    """保存済みの下書き一覧を表示"""
    drafts = sorted(Path("drafts").glob("*.md"))
    if not drafts:
        print("\n📂 下書きがありません。`python main.py run` で記事を生成してください。")
        return

    print(f"\n📂 下書き一覧（{len(drafts)}件）\n")
    for i, f in enumerate(drafts, 1):
        size_kb = f.stat().st_size / 1024
        print(f"  {i}. {f.name}  ({size_kb:.1f} KB)")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    dispatch = {"run": cmd_generate, "research": cmd_research, "list": cmd_list}
    action = dispatch.get(cmd)
    if action:
        action()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
