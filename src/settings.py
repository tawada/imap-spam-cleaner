import os


def get_setting_dirs():
    """
    設定ディレクトリを取得する関数
    :return: 設定ディレクトリのリスト
    """

    # 設定ディレクトリのリスト
    setting_dirs = []

    # デフォルトの設定ディレクトリ以外の設定ディレクトリを取得
    for dirpath, dirnames, filenames in os.walk("settings"):
        for dirname in dirnames:
            if dirname != "default":
                setting_dirs.append(dirname)

    return setting_dirs
