# 自動更新の初期設定

このリポジトリはPublicです。認証情報をファイルとしてコミットしないでください。

## Google側（初回のみ）

1. Google Cloudプロジェクトを用意し、Google Sheets APIを有効化する。
2. 専用のサービスアカウントを作成する。学習記録の参照専用とし、広範なIAM権限を付けない。
3. サービスアカウントのJSON鍵を発行する（安全に保管する）。
4. PMP学習スプレッドシートの「共有」でサービスアカウントのメールアドレスを**閲覧者**として追加する。スプレッドシートを一般公開する必要はない。

## GitHub側（初回のみ）

Settings → Secrets and variables → Actions で設定する。

- Repository secret `GOOGLE_SERVICE_ACCOUNT_JSON`: JSON鍵の**内容全文**
- Repository secret `PMP_SPREADSHEET_ID`: 対象スプレッドシートのID
- Repository variable `GIT_COMMIT_EMAIL`: GitHubアカウントに登録・検証済みのメールアドレス（GitHub noreplyアドレスでも可）

Settings → Actions → General → Workflow permissions で、必要に応じて **Read and write permissions** を許可する。組織ポリシーが優先する場合は管理者に確認する。

## 動作確認

Actions → Update learning journal → Run workflow を実行し、ログが成功していること、README・data/progress.json・logs/ が更新されることを確認する。

以後、毎日22:30 JSTに自動実行する（GitHub Actionsのスケジュールは混雑により遅延することがある）。

## セキュリティ

- 鍵はGitHub Secretsにのみ登録し、チャットやIssueに貼らない。
- サービスアカウントには対象スプレッドシートの閲覧権限だけを付ける。
- 鍵の漏えいが疑われる場合は失効・再発行する。
- 本方式はJSON鍵を使う簡易構成。長期運用ではWorkload Identity Federationによる鍵レス認証が望ましい。
- 学習した日ではなくGitHubにコミットした日がContribution Graphの基本となる。
