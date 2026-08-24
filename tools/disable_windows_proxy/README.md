# Audion Disable Windows Proxy

Small portable helper for cleaning stale Windows proxy settings such as `127.0.0.1:12334` left by local proxy clients.

## What it does

- Backs up current registry proxy settings to `backup/proxy_YYYYMMDD_HHMMSS/`.
- Disables the current user's WinINet/System Proxy setting.
- Removes stale `ProxyServer` and `ProxyOverride` values.
- Removes `AutoConfigURL` by default.
- Disables `AutoDetect` by default.
- Clears the WinINet connection cache values that may keep old proxy settings visible in Windows Settings.
- Can reset WinHTTP proxy separately with administrator rights.
- Writes logs to `logs/`.

## Recommended order

1. Run `Run_Check_Proxy_Status.cmd`.
2. Run `Run_Disable_Proxy_Current_User.cmd` as the normal current user.
3. Run `Run_Check_Proxy_Status.cmd` again.
4. If WinHTTP still shows a proxy, run `Run_Reset_WinHTTP_Proxy_Admin.cmd`.

## Hiddify / local proxy usage without touching Windows System Proxy

Use Hiddify as a local proxy only:

- Keep `System Proxy` / `Set system proxy` disabled in Hiddify.
- Keep `TUN Mode` disabled unless you intentionally want whole-system routing.
- Keep the client running only when needed.
- Configure only the app that needs proxy access to use the local proxy manually.

Typical local endpoint:

```text
127.0.0.1:12334
```

Examples:

```cmd
curl -x http://127.0.0.1:12334 https://example.com
```

```cmd
git -c http.proxy=http://127.0.0.1:12334 -c https.proxy=http://127.0.0.1:12334 clone https://github.com/example/repo.git
```

For browsers, use a browser proxy profile/extension and switch between proxy and direct mode inside the browser instead of enabling Windows System Proxy.

## Restore

Backups are `.reg` files stored in `backup/proxy_YYYYMMDD_HHMMSS/`.
Double-click a backup `.reg` file only if you intentionally want to restore the previous proxy state.
