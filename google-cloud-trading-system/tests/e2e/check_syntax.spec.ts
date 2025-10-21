import { test, expect } from '@playwright/test';

test.describe('JavaScript Syntax Check', () => {
  test('should check JavaScript syntax in page source', async ({ page }) => {
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    
    // Get the page content
    const content = await page.content();
    
    // Find the script section
    const scriptMatch = content.match(/<script>(.*?)<\/script>/s);
    if (scriptMatch) {
      const scriptContent = scriptMatch[1];
      console.log('Script content length:', scriptContent.length);
      
      // Check for common syntax issues
      const issues = [];
      
      // Check for unmatched parentheses
      const openParens = (scriptContent.match(/\(/g) || []).length;
      const closeParens = (scriptContent.match(/\)/g) || []).length;
      if (openParens !== closeParens) {
        issues.push(`Unmatched parentheses: ${openParens} open, ${closeParens} close`);
      }
      
      // Check for unmatched braces
      const openBraces = (scriptContent.match(/\{/g) || []).length;
      const closeBraces = (scriptContent.match(/\}/g) || []).length;
      if (openBraces !== closeBraces) {
        issues.push(`Unmatched braces: ${openBraces} open, ${closeBraces} close`);
      }
      
      // Check for unmatched brackets
      const openBrackets = (scriptContent.match(/\[/g) || []).length;
      const closeBrackets = (scriptContent.match(/\]/g) || []).length;
      if (openBrackets !== closeBrackets) {
        issues.push(`Unmatched brackets: ${openBrackets} open, ${closeBrackets} close`);
      }
      
      console.log('Syntax Issues:', issues);
      
      // Look for specific problematic patterns
      if (scriptContent.includes('});')) {
        console.log('Found }); pattern');
      }
      if (scriptContent.includes('};')) {
        console.log('Found }; pattern');
      }
      
      // Check around the initAIAssistant function
      const aiAssistantMatch = scriptContent.match(/function initAIAssistant\(\)\s*\{([\s\S]*?)\}/);
      if (aiAssistantMatch) {
        console.log('initAIAssistant function found, length:', aiAssistantMatch[1].length);
      } else {
        console.log('initAIAssistant function not found or malformed');
      }
    } else {
      console.log('No script section found');
    }
  });
});

