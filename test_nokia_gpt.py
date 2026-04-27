import pyperclip
from bs4 import BeautifulSoup
from seleniumbase import BaseCase
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

import json
import os
import time
import pytest

class LoadSessionData(BaseCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_cookies(self, file_path="cookies.txt"):        
        if not os.path.exists(file_path):
            return
        try:
            with open(file_path, 'r') as file:
                cookies = json.load(file)
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            print(f"Cookies loaded from {file_path}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from file {file_path}: {e}")
        except Exception as e:
            print(f"An error occurred while loading cookies from file {file_path}: {e}")

    def save_cookies(self, file_path="cookies.txt"):
        try:
            with open(file_path, 'w') as file:
                json.dump(self.driver.get_cookies(), file)
            print(f"Cookies saved to {file_path}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from file {file_path}: {e}")
        except Exception as e:
            print(f"An error occurred while saving cookies to file {file_path}: {e}")

    def load_local_storage(self, file_path="local_storage.json"):
        if not os.path.exists(file_path):
            return
        try:
            with open(file_path, 'r') as file:
                local_storage = json.load(file)
            # 使用 JavaScript 直接设置 Local Storage，一般是在页面加载之后设置
            # for key, value in local_storage.items():
            #     self.driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)
            # 使用 CDP 注入 JavaScript，在页面加载时自动设置 Local Storage，一般在页面加载之前设置
            # 注意：要用单引号包括key和value，否则会和JSON中的双引号冲突
            self.driver.execute_cdp_cmd(
                'Page.addScriptToEvaluateOnNewDocument',
                {
                    'source': ''.join(
                        [f"window.localStorage.setItem('{k}', '{v}');" for k, v in local_storage.items()]
                    )
                }
            )
            print(f"LocalStorage loaded from {file_path}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from file {file_path}: {e}")
        except Exception as e:
            print(f"An error occurred while loading localStorage from file {file_path}: {e}")

    def save_local_storage(self, file_path="local_storage.json"):
        try:
            local_storage = self.driver.execute_script("return Object.assign({}, window.localStorage);")
            with open(file_path, 'w') as file:
                json.dump(local_storage, file)
            print(f"LocalStorage saved to {file_path}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from file {file_path}: {e}")
        except Exception as e:
            print(f"An error occurred while saving localStorage to file {file_path}: {e}")

class CompanyGPTAutomation(LoadSessionData):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 从环境变量中获取用户名和密码
        self.username = os.getenv("COMPANY_GPT_USERNAME")
        self.password = os.getenv("COMPANY_GPT_PASSWORD")

    def login(self):
        # 检查页面是否跳转到Sign-in页面
        try:
            WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[type="email"]'))
            ).send_keys(self.username)
            print("Entered email")
            next_button = self.find_element('input[type="submit"]')
            next_button.click()
            print("Clicked Next button")
        except Exception as e:
            print(f"No email input found")

        # 输入密码
        try:
            WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[type="password"'))
            ).send_keys(self.password)
            print("Entered password")
            next_button = self.find_element('input[type="submit"]')
            next_button.click()
            print("Clicked Sign button")
        except Exception as e:
            print(f"No password input found: {e}")

        # 循环执行 2 次, 忽略alert(针对firefox)
        # for i in range(2):
        #     try:
        #         WebDriverWait(self.driver, 1).until(
        #             EC.alert_is_present()
        #         )
        #         alert = self.driver.switch_to.alert
        #         alert.accept()
        #         print(f"Accepted alert {i+1}")
        #     except Exception as e:
        #         print(f"No alert found on iteration {i+1}: {e}")
    
    def send_prompt_and_get_output(self, prompt, headless):
        if not headless:
            try:
                # 使用 XPath 查找初始状态的 <span> 节点
                placeholder_span = self.find_element(By.XPATH, '//span[@data-slate-placeholder="true"]')
                print("Found placeholder span element")
            except Exception as e:
                pytest.fail("Placeholder span element not found")

            try:
                # 模拟用户鼠标点击行为
                actions = ActionChains(self.driver)
                actions.move_to_element(placeholder_span).click().perform()
                print("Clicked on placeholder span element")
            except Exception:
                pytest.fail("Failed to click on placeholder span element")

        # 输入自定义内容
        editor = self.find_element('.slate-editor[contenteditable="true"]')
        if not headless:
            # 使用JavaScript点击输入框
            self.driver.execute_script("arguments[0].click();", editor)
            pyperclip.copy(prompt)
            # 模拟 Ctrl+V 粘贴操作
            actions = ActionChains(self.driver)
            actions.move_to_element(editor).click().key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        else:
            # 直接用 JS 赋值并触发事件
            self.driver.execute_script("""
                arguments[0].focus();
                arguments[0].innerText = arguments[1];
                arguments[0].scrollTop = arguments[0].scrollHeight;
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, editor, prompt)

        WebDriverWait(self.driver, 2).until(lambda d: editor.text != "")
        print("Entered prompt content")

        try:
            # 找到发送按钮并点击
            send_button = self.find_element(By.XPATH, '//button[.//span[@aria-label="arrow-up"]]') # By.XPATH的属性需要加@
            send_button.click()
            print("Clicked Send button")
        except Exception as e:
            pytest.fail('Send button not found')

        # 发送prompt之后截图
        self.driver.save_screenshot(f'{self.screenshot_path}-1.png')
        print(f'Screenshot saved to {self.screenshot_path}-1.png')
        try:
            # 等待输出生成
            WebDriverWait(self.driver, 20).until(
                EC.visibility_of_element_located((By.XPATH, '//div[@class="chat-message"]//div[@id="message-bubble0"][.//strong[text()="CompanyGPT:"]]'))
            )
            print("Output message bubble found")
            time.sleep(20)
            message_bubble = self.find_element(By.XPATH, '//div[@class="chat-message"]//div[@id="message-bubble0"][.//strong[text()="CompanyGPT:"]]').get_attribute("outerHTML")
            return message_bubble
        except Exception:
            # 发送prompt之后截图
            self.driver.save_screenshot(f'{self.screenshot_path}-2.png')
            print(f'Screenshot saved to {self.screenshot_path}-2.png')
            pytest.fail("Failed to get output message bubble")

    def choose_best_mode(self):
        models_priority = ["GPT-4o", "O3 mini", "Claude 3.5 Sonnet V2", "Gemini 1.5 Flash", "Llama 3.1"]
        quota_available = False
        for model_name in models_priority:
            button = self.find_element(By.XPATH, f'//button[span[2][text()="Gemini 1.5 Flash"]]')
            button.click()
            print("Clicked button")
            # 等待并点击下拉列表中的 <li> 选项
            try:
                WebDriverWait(self.driver, 2).until(
                    EC.visibility_of_element_located((By.XPATH, f'//ul/li[.//b[text()="{model_name}"]]'))
                ).click()
                print("Clicked <li> element")
            except Exception as e:
                print(f'<li> element with <b> text "{model_name}" not found: {e}')

            try:
                # 计算消息剩余条数
                left_message_count = self.find_element(By.XPATH, '//span[text()[4][contains(., "messages left for today")]]').text.split()[0]
                left_message_count = left_message_count.split('/')[0]
                print(f'Found span with text containing "messages left for today", count = {left_message_count}')
                if left_message_count and int(left_message_count) > 0:
                    quota_available = True
                    break
            except Exception as e:
                print(f'Span with text containing "messages left for today" not found: {e}')
        if not quota_available:
            pytest.fail("No quota available for any model")

    def authenticate_and_wait_for_ready(self):
        authenticated = False
        try:
            WebDriverWait(self.driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, f'//button[span[2][text()="Gemini 1.5 Flash"]]'))
            )
            print('Authenticated with local storage')
            self.save_local_storage("local_storage.json")
            authenticated = True
        except Exception as e:
            print('Not authenticated with local storage')

        if not authenticated:
            self.login()

        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//body/div[@class="ReactModalPortal"]/div[@class="ReactModal__Content ReactModal__Content--after-open"]'))
            )
            close_button = self.find_element(By.XPATH, '//body/div[@class="ReactModalPortal"]/div[@class="ReactModal__Content ReactModal__Content--after-open"]//button')
            close_button.click()
            print('Close button clicked')
        except Exception as e:
            print('Close button not found')

        # 等待页面button元素，并且子元素span中的内容是"Gemini 1.5 Flash"(缺省)，点击button，选择模型
        try:
            WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.XPATH, f'//button[span[2][text()="Gemini 1.5 Flash"]]'))
            )
            print(f'Button with text "Gemini 1.5 Flash" found')
            # self.save_cookies()
            self.save_local_storage()
        except Exception as e:
            pytest.fail(f'Button with text "Gemini 1.5 Flash" not found')

    def auto_login_and_submit(self, prompt, headless=False):
        # 设置 Firefox 驱动
        self.driver_path = "chromedriver"  # 如果 geckodriver 在 PATH 中，无需更改；否则填写具体路径
        # 启动浏览器
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-user-data-dir")

        self.driver = webdriver.Chrome(options=options)  # 等同于self.get_new_driver("firefox")，但是可以自定义配置，比如profile

        # 设置浏览器全屏
        self.driver.maximize_window()

        # 设置页面加载超时
        self.driver.set_page_load_timeout(30)  # 设置页面加载超时时间为30秒

        # 导入 cookies可能会导致服务器端出问题，所以暂时不导入
        # self.load_cookies()

        # 导入 localStorage（在页面加载之前导入，基于CDP）
        # self.load_local_storage()

        # 打开 Company GPT 页面
        self.get("https://gpt.company.example.com")

        print("Opened Company GPT page")

        # 忽略alert(针对firefox)
        # try:
        #     WebDriverWait(self.driver, 1).until(
        #         EC.alert_is_present()
        #     )
        #     alert = self.driver.switch_to.alert
        #     alert.accept()
        #     print(f"Accepted alert")
        # except Exception as e:
        #     print(f"No alert found: {e}")

        self.authenticate_and_wait_for_ready()
        self.choose_best_mode()
        return self.send_prompt_and_get_output(prompt, headless)

class TestCompanyGPTAutomation(CompanyGPTAutomation):
    def setUp(self):
        super().setUp()
        # 其他初始化代码

    def remove_copy_button(self, html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for div in soup.find_all("div", class_="copy-button"):
                div.decompose()  # 移除该元素
        except Exception as e:
            print(f"Failed to remove copy button: {e}")
            return html_content
        return str(soup)

    # 需要手动注入request fixture，因为BaseCase使用的是unittest.TestCase，而pytest使用的是pytest.Function
    @pytest.fixture(autouse=True)
    def inject_fixtures(self, request):
        self.request = request

    def test_auto_login_and_submit(self):
        prompt = """请审查以下代码，重点关注内存管理、线程同步、网络堵塞及第三方库正确调用方面的问题。若发现网络相关的代码，请评估是否存在可能引起阻塞的情况，并建议如何优化。

输出格式：
<p><strong>文件路径:</strong> [文件路径]</p>
<p><strong>函数名称:</strong> [函数名称]</p>
<p><strong>函数位置:</strong> [函数所在的文件位置的行号范围]</p>

<p><strong>问题描述与改进意见:</strong></p>

<p><strong>问题描述:</strong><br>[简述发现的问题，特别强调与内存安全、线程安全、网络堵塞或第三方库使用相关的内容。]</p>
<p><strong>改进意见:</strong><br>[提出具体的改进建议以解决上述问题。]</p>

<p><strong>问题描述:</strong><br>[简述发现的另一个问题]</p>
<p><strong>改进意见:</strong><br>[提出具体的改进建议以解决该问题。]</p>

[...更多问题和改进意见...]

注意：
1. **无需进行函数参数中的指针非空检查**。
2. **无需针对输入指针或者类成员指针做非空判断**
3. **无需对已正确使用的智能指针（如`std::shared_ptr`）和同步机制（如`LockGuard`）提供问题描述和改进意见**
4. **无需要求对函数返回值做处理**
5. **类似的错误无需重复描述, 只需要对第一次出现错误的地方做描述即可**

示例：
文件路径: src/core/handlers/cnum/LdapConfigManager.cpp
函数: bool LdapConfigManager::saveLdapConfigParamsToFile(const LdapConfigParams& params, const std::string& filePath)
- 问题描述: 在多线程环境下共享变量未使用任何同步机制保护，可能导致数据竞争。
- 改进意见: 使用互斥锁或其他同步机制来保护共享资源，确保线程安全。

代码如下：
"""
        output_file = self.request.config.getoption("--output")
        if os.path.exists(output_file):
            os.remove(output_file)
        headless = self.request.config.getoption("--headless")
        commit_functions = self.request.config.getoption("--commit-functions")
        if not os.path.exists(commit_functions):
            pytest.fail(f"Commit functions file {commit_functions} not found")
        screenshot_dir = os.path.dirname(os.path.abspath(output_file))
        commit_functions_filename = os.path.basename(commit_functions)
        commit_functions_filename_without_ext = commit_functions_filename.split('.')[0]
        self.screenshot_path = os.path.join(screenshot_dir, f'{commit_functions_filename_without_ext}.screenshot')
        try:
            with open(commit_functions, 'r') as file:
                code_changes = file.read()
            html = self.auto_login_and_submit(f"{prompt}{code_changes}", headless)
            with open(output_file, 'w') as file:
                file.write(html)
        except Exception as e:
            pytest.fail(f"Error: {e}")
        finally:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()

# 运行测试
if __name__ == "__main__":
    pytest.main()
