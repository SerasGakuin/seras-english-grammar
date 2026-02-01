#!/bin/bash
# Git hooks をセットアップするスクリプト
#
# 使用方法:
#   ./scripts/setup_hooks.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_SRC="$SCRIPT_DIR/hooks"
HOOKS_DST="$PROJECT_ROOT/.git/hooks"

echo "Git hooks をセットアップ中..."

# hooks ディレクトリが存在するか確認
if [ ! -d "$HOOKS_SRC" ]; then
    echo "Error: $HOOKS_SRC が見つかりません"
    exit 1
fi

# 各hookをコピー
for hook in "$HOOKS_SRC"/*; do
    if [ -f "$hook" ]; then
        hook_name=$(basename "$hook")
        cp "$hook" "$HOOKS_DST/$hook_name"
        chmod +x "$HOOKS_DST/$hook_name"
        echo "  ✅ $hook_name"
    fi
done

echo ""
echo "セットアップ完了"
