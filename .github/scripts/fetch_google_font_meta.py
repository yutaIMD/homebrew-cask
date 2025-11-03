import sys
import re
import httpx
import os

# --- 設定 ---
# google/fontsリポジトリのMETADATA.pbファイルへのRAWアクセスURLのテンプレート
# {font_id} の部分が後で置換されます
METADATA_URL_TEMPLATE = "https://raw.githubusercontent.com/google/fonts/main/ofl/{font_id}/METADATA.pb"
# ----------------

def get_font_id_from_cask(content):
    """
    Caskファイルの内容からGoogle FontsのURLを見つけ、font_idを抽出する
    例: "github.com/google/fonts/raw/main/ofl/notosansjp" -> "notosansjp"
    """
    # Google FontsのURLパターン（ofl/xxx の部分が欲しい）
    match = re.search(r'github\.com/google/fonts/.*?/ofl/([a-zA-Z0-9_-]+)', content)
    if match:
        return match.group(1)
    return None

def fetch_languages_from_metadata(font_id):
    """
    METADATA.pbファイルを取得し、'subsets:' 行から言語リストを抽出する
    """
    url = METADATA_URL_TEMPLATE.format(font_id=font_id)
    languages = []
    
    try:
        response = httpx.get(url)
        response.raise_for_status() # 404などのエラーチェック

        for line in response.text.splitlines():
            if line.strip().startswith('subsets:'):
                # 'subsets: "japanese"' -> 'japanese'
                lang = line.split('"')[1]
        
        return sorted(list(set(languages))) # 重複除去とソート

    except httpx.HTTPStatusError as e:
        print(f"Error fetching metadata for {font_id} (Status: {e.response.status_code}): {url}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        
    return None

def update_cask_file(cask_path, languages, font_id):
    """
    Caskファイルの先頭にメタデータコメントを追記する
    """
    if not languages:
        print(f"No languages found for {font_id}. Skipping update.")
        return False

    # メタデータブロックの作成
    lang_list_str = ", ".join([f'"{lang}"' for lang in languages])
    meta_block = f"""# --- BEGIN CUSTOM METADATA ---
# meta:
#   language: [{lang_list_str}]
#   style: "auto-detect-pending" # styleは別途対応
#   source: "google-fonts"
#   font_id: "{font_id}"
# --- END CUSTOM METADATA ---

"""
    
    try:
        with open(cask_path, 'r+', encoding='utf-8') as f:
            content = f.read()
            
            # 既にメタデータが存在しないかチェック
            if "# --- BEGIN CUSTOM METADATA ---" in content:
                print(f"Metadata already exists in {cask_path}. Skipping.")
                return False
            
            # ファイルの先頭にメタデータを書き込む
            f.seek(0) # ファイルポインタを先頭に戻す
            f.write(meta_block + content)
            print(f"Successfully added metadata to {cask_path}")
            return True
            
    except Exception as e:
        print(f"Error writing to {cask_path}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_google_font_meta.py <path_to_cask_file>")
        sys.exit(1)

    cask_path = sys.argv[1]

    if not os.path.exists(cask_path):
        print(f"File not found: {cask_path}")
        sys.exit(1)
        
    try:
        with open(cask_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {cask_path}: {e}")
        sys.exit(1)
        
    # 1. Google Fonts由来かチェック
    font_id = get_font_id_from_cask(content)
    
    if not font_id:
        print(f"{cask_path} does not seem to be a Google Font (ofl). Skipping.")
        sys.exit(0) # エラーではなく正常終了

    print(f"Found Google Font ID: {font_id}")

    # 2. METADATA.pbから言語情報を取得
    languages = fetch_languages_from_metadata(font_id)
    
    if languages:
        print(f"Found languages: {languages}")
        # 3. Caskファイルにメタデータを書き込む
        update_cask_file(cask_path, languages, font_id)
    else:
        print(f"Could not retrieve languages for {font_id}.")

if __name__ == "__main__":
    main()