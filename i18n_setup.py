import i18n
import os
from config import ConfigManager

# グローバルな翻訳関数プレースホルダ
# 実際の翻訳関数は init_i18n 関数内で設定されます。
def translate_placeholder(key, **kwargs):
    """初期化前のプレースホルダー翻訳関数"""
    # kwargs を含めて、初期化後に実際の翻訳関数が呼ばれた際にも対応できるようにする
    return f"_{key}_" # 初期化前はキーをそのまま返すか、目印をつける

_translator_func = translate_placeholder

def init_i18n():
    """国際化設定を初期化し、翻訳関数をグローバルに設定する"""
    global _translator_func
    config_manager = ConfigManager()
    current_language = config_manager.get_language()
    print(f"DEBUG: init_i18n called. Target language: {current_language}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    locales_path = os.path.normpath(os.path.join(script_dir, 'locales'))

    print(f"DEBUG: i18n_setup.py __file__: {__file__}")
    print(f"DEBUG: Calculated (normalized) locales_path: {locales_path}")

    if not (os.path.exists(locales_path) and os.path.isdir(locales_path)):
        print(f"ERROR: locales_path does not exist or is not a directory: {locales_path}")
        _translator_func = translate_placeholder # フォールバック
        return # これ以上進めない

    print(f"DEBUG: locales_path exists and is a directory. Contents: {os.listdir(locales_path)}")

    # i18nライブラリのグローバル設定を毎回行う
    i18n.load_path.clear()
    i18n.load_path.append(locales_path)
    i18n.set('file_format', 'json')
    i18n.set('filename_format', '{locale}.{format}')
    i18n.set('fallback', 'en')
    i18n.set('locale', current_language)

    i18n.set('error_on_missing_translation', True)
    i18n.set('error_on_missing_file', True)

    print(f"DEBUG: i18n settings post-set: locale='{i18n.get('locale')}', load_path={i18n.get('load_path')}")

    try:
        _translator_func = i18n.t
        print(f"i18n re-initialized. Language: {i18n.get('locale')}. _translator_func is now i18n.t")

        test_keys = ['launcher.title', 'settings.title', 'settings.api.title'] # いくつかキーをテスト
        for test_key in test_keys:
            translated_text = _(test_key)
            print(f"DEBUG: Test translation for '{test_key}' via _ wrapper: {translated_text}")
            if translated_text == test_key or translated_text == f"_{test_key}_":
                print(f"WARNING: Test translation for '{test_key}' did not yield expected result.")

    except Exception as e:
        print(f"ERROR during i18n (re-)initialization or test translation: {e}")
        _translator_func = translate_placeholder
        import traceback
        print(traceback.format_exc())

def _(key, **kwargs):
    """グローバルに公開する翻訳ラッパー関数"""
    return _translator_func(key, **kwargs)

def get_translator():
    """現在の翻訳ラッパー関数を返す"""
    return _

# アプリケーション起動時に一度だけ呼び出すことを想定
# init_i18n() # main.py で呼び出される

# 使用例 (他のモジュールから):
# from i18n_setup import _
# translated_text = _('some.translation.key')

# 言語変更時に呼び出す関数
def change_language(language_code):
    """言語設定を変更し、i18nを再初期化する"""
    config_manager = ConfigManager()
    config_manager.set_language(language_code)
    init_i18n() # 設定を再読み込みしてi18nを更新
    print(f"Language changed to: {language_code}")
    # UIの再描画などが必要な場合は、別途通知/コールバック機構が必要
    return get_translator()

if __name__ == '__main__':
    # テスト用
    init_i18n()
    # ja.json に {"test.greeting": "こんにちは、{name}！"} がある想定
    print(f"Default language: {_('test.greeting', name='ワールド')}")

    # locales/ja.json (テスト用)
    # {
    #     "test.greeting": "こんにちは、{name}！"
    # }
    # locales/en.json (テスト用)
    # {
    # #    "test.greeting": "Hello, {name}!"
    # # }

    # change_language('en')
    # print(f"English: {_('test.greeting', name='World')}")
    pass
