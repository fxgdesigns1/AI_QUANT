import { test, expect } from '@playwright/test';

test.describe('JavaScript Syntax Debug', () => {
  test('should find the exact JavaScript syntax error', async ({ page }) => {
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    
    // Get the page content and extract JavaScript
    const content = await page.content();
    const scriptMatch = content.match(/<script>(.*?)<\/script>/s);
    
    if (scriptMatch) {
      const scriptContent = scriptMatch[1];
      console.log('Script length:', scriptContent.length);
      
      // Try to evaluate the script piece by piece to find the error
      const lines = scriptContent.split('\n');
      console.log('Total lines:', lines.length);
      
      // Look for common syntax issues
      let lineNumber = 1;
      for (const line of lines) {
        // Check for unmatched quotes in template strings
        if (line.includes('`') && line.includes('${')) {
          const backticks = (line.match(/`/g) || []).length;
          if (backticks % 2 !== 0) {
            console.log(`Line ${lineNumber}: Unmatched backticks:`, line.trim());
          }
        }
        
        // Check for unmatched parentheses in function calls
        if (line.includes('(') && line.includes(')')) {
          const openParens = (line.match(/\(/g) || []).length;
          const closeParens = (line.match(/\)/g) || []).length;
          if (openParens !== closeParens) {
            console.log(`Line ${lineNumber}: Unmatched parentheses:`, line.trim());
          }
        }
        
        // Check for template string issues
        if (line.includes('${') && !line.includes('`')) {
          console.log(`Line ${lineNumber}: Template string without backticks:`, line.trim());
        }
        
        lineNumber++;
      }
      
      // Try to find the specific error by testing script execution
      try {
        await page.evaluate(() => {
          // Try to execute the script content
          const script = document.querySelector('script');
          if (script) {
            console.log('Script element found');
            console.log('Script content length:', script.textContent?.length);
          }
        });
      } catch (error) {
        console.log('Script execution error:', error.message);
      }
      
      // Look for specific problematic patterns
      const problematicPatterns = [
        /`[^`]*\$\{[^}]*$/m,  // Unclosed template string
        /\([^)]*$/m,          // Unclosed function call
        /function[^{]*$/m,    // Unclosed function declaration
        /if[^{]*$/m,          // Unclosed if statement
      ];
      
      for (const pattern of problematicPatterns) {
        const matches = scriptContent.match(pattern);
        if (matches) {
          console.log('Problematic pattern found:', matches[0]);
        }
      }
    }
  });
});

