import asyncio
import traceback
from collections import OrderedDict

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from lib.clash_service import ClashService
from lib.discord_manager import send_discord_notification



def get_sizes(html, target_sizes):
    soup = BeautifulSoup(html, 'lxml')  # 改用lxml解析器

    # 查找颜色选择容器
    color_selectable = soup.find('hmf-selectable')
    if color_selectable:
        print("找到尺寸选择区域")

        for target_size in target_sizes:
            # 使用CSS选择器模糊匹配类名和属性
            buttons = color_selectable.select(f'button[class*="hmf-option-contained"][aria-label="{target_size}"]')

            for button in buttons:
                if 'hmf-option-unavailable' in button.get('class', []):
                    print(f"尺寸 {target_size} 不可用：no")

                else:
                    print(f"尺寸 {target_size} 可用：yes")
                    return True
    else:
        print("未找到尺寸选择区域")
        return False

async def scrape_with_proxy(url, clash_service, target_sizes):
    try_time = 5

    while try_time > 0:
        try_time -= 1
        clash_service.switch()

        async with async_playwright() as p:
            # 启动浏览器并设置代理
            browser = await p.chromium.launch(
                headless=False,
                proxy={
                    "server": clash_service.http_proxy,
                }
            )
            page = await browser.new_page()

            try:
                # 访问页面并等待动态内容加载
                await page.goto(url, timeout=10000)
                await page.wait_for_selector("div.description-container", state="visible", timeout=10000)  # 确保基础元素加载

                # 获取完整 HTML
                html = await page.content()
                print(f"成功抓取 {url} 的 HTML（代理：{clash_service.http_proxy}）")

            except Exception as e:
                print(f"抓取失败：{url} | 错误：{str(e)}")
                html = None
                await browser.close()
                continue

            await browser.close()

        if html and get_sizes(html, target_sizes):
            try:
                await send_discord_notification(f"有货!!!!: {url}", clash_service.http_proxy)
            except Exception:
                traceback.print_exc()
            finally:
                break


async def main():
    # frequency = int(input("input a checking frequency(second): "))
    frequency = 60

    # 读取links.txt
    links = OrderedDict()
    with open("links.txt", 'r') as links_file:
        links_lines = [l.replace('\n', '').replace('\r', '') for l in links_file.readlines() if l]
        links_num = len(links_lines) // 2
        for i in range(links_num):
            links[links_lines[i*2]] = links_lines[i*2+1].split(',')

    # 启动clash
    clash_services = []
    for i in range(1, links_num+1):
        clash_services.append(ClashService(7890 if i == 1 else clash_services[-1].external_controller_port+1, i))

    while True:
        # for c in clash_services:
        #     c.switch()
        # 并发浏览links
        results = await asyncio.gather(
            *[scrape_with_proxy(url, clash_service, target_sizes) for (url, target_sizes), clash_service in zip(links.items(), clash_services)]
        )
        await asyncio.sleep(frequency)


if __name__ == "__main__":
    asyncio.run(main())