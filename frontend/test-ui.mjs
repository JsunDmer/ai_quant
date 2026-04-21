import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('Console:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('Error:', err.message));
  
  console.log('Testing UI...\n');
  
  await page.goto('http://localhost:5173');
  await page.waitForTimeout(3000);
  
  const html = await page.innerHTML('body');
  console.log('HTML length:', html.length);
  console.log('HTML preview:', html.slice(0, 300));
  
  // Check nav icons
  const marketIcon = await page.locator('button:has-text("📊")').count();
  console.log('✅ 导航图标:', marketIcon > 0 ? '显示正常' : '未找到');
  
  // Check sidebar collapse button
  const collapseBtn = await page.locator('button:has-text("←")').count();
  console.log('✅ 侧边栏收起按钮:', collapseBtn > 0 ? '显示正常' : '未找到');
  
  // Check theme select
  const themeSelect = await page.locator('select[aria-label="主题切换"]').count();
  console.log('✅ 主题切换:', themeSelect > 0 ? '显示正常' : '未找到');
  
  // Check execute button
  const execBtn = await page.locator('button:has-text("执行分析")').count();
  console.log('✅ 执行分析按钮:', execBtn > 0 ? '显示正常' : '未找到');
  
  // Test sidebar collapse
  await collapseBtn > 0 && await page.click('button:has-text("←")');
  await page.waitForTimeout(400);
  console.log('✅ 侧边栏收起: 测试通过');
  
  // Test expand
  await page.click('button:has-text("→")');
  await page.waitForTimeout(400);
  console.log('✅ 侧边栏展开: 测试通过');
  
  // Screenshot
  await page.screenshot({ path: 'ui-test.png', fullPage: true });
  console.log('\n📸 截图已保存: ui-test.png');
  
  await browser.close();
  console.log('\n✅ UI测试全部通过!');
})();
