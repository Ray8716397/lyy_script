# lyy_script

https://github.com/doreamon-design/clash/releases

切换节点:
curl -X PUT "http://127.0.0.1:10001/proxies/Proxies" -H "Content-Type: application/json"   -d '{"name": "🇭🇰 HKG 01"}'

测试当前节点延迟:
curl -X GET "http://127.0.0.1:10001/proxies/Proxies/delay?timeout=5000&url=https://www.google.com"